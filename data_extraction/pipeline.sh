#!/bin/bash

build_dir=false
build_cmd='cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Debug ..'

codegraph_tool_path=""
project_name=""
project_git=""

while [ -n "$1" ]
do
case "$1" in
-h) echo "USAGE: pipeline.sh --codegraph_tool-path 'codegraph_tool' --project-name 'llvm' --project-git 'https://github.com/llvm/llvm-project' [--bear] [--build-dir] [--build-cmd 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Debug ..']"
exit 0;;
--help) echo "USAGE: pipeline.sh --codegraph_tool-path 'codegraph_tool' --project-name 'llvm' --project-git 'https://github.com/llvm/llvm-project' [--bear] [--build-dir] [--build-cmd 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Debug ..']"
exit 0;;
--codegraph_tool-path) codegraph_tool_path="$2"
shift ;;
--project-name) project_name="$2"
shift ;;
--project-git) project_git="$2"
shift ;;
--bear) build_cmd="bear -- make" ;;
--build-dir) build_dir=true
shift ;;
--build-cmd) build_cmd="$2"
shift ;;
--) shift
break ;;
*) echo "$1 is not an option"
exit 1;;
esac
shift
done

if [ "$codegraph_tool_path" = "" ] ; then
  echo "codegraph_tool_path is required"
  exit 1
fi

if [ "$project_name" = "" ] ; then
  echo "$project_name is required"
  exit 1
fi

if [ "$project_git" = "" ] ; then
  echo "$project_git is required"
  exit 1
fi


# print specified arguments
echo "$codegraph_tool_path $project_name $project_git $build_dir $build_cmd"

# make a separate directory
mkdir "$project_name" && cd "$project_name" || exit
project_path=$("pwd")

# clone the repository
git clone --depth=1 "$project_git"
folder=$("ls")
echo "Cloned '$folder'"

# compute code lines statistics
cloc --json "$folder" > cloc.json

# copy codegraph_tool into folder to run locally (it generates some files nearby)
cp "$codegraph_tool_path" "./codegraph_tool"
./codegraph_tool --version


# extract commit dates (in parallel)
for number in 0 1 2 3 4 5 6 7
do
  python3 ../commit_dates.py "$folder" commit_dates.json 8 $number &
done
wait
python3 ../commit_dates.py "$folder" commit_dates.json 8
for number in 0 1 2 3 4 5 6 7
do
  rm "${number}_commit_dates.json"
done


cd "$folder" || exit

# mkdir build if specified
if [ "$build_dir" = true ] ; then
  mkdir "build" && cd "build" || exit
fi

# build project
eval "$build_cmd"

cc_json_dir=$("pwd")

# build callgraph
cd "$project_path" || exit
./codegraph_tool index --compile-commands-dir "$cc_json_dir" --index-database-path codegraph_tool.db --ignore-diags=false --strip-unknown-options --verbose --query-driver=false
./codegraph_tool query --index-database-path codegraph_tool.db --pretty-print --arango-nodes=nodes --arango-edges=edges < ../db_query.json > out.json

# collect statistics into a table
python3 ../db_stat.py --nodes-path nodes.json --project-path "$project_path" --project-root "$folder" --db-path "codegraph_tool.db" --out_path "db_stat.csv"

# merge commit dates into table
python3 ../merge_commits.py --table-path "db_stat.csv" --db-path "codegraph_tool.db" --commits-path "commit_dates.json" --out-path "${project_name}_final.csv"
