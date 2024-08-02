import re

import streamlit as st


def pending(s, module=st, unsafe_allow_html=True):
    s = s.replace("\n", "<br>")
    module.markdown(f'<p class="pending-text">{s}</p>', unsafe_allow_html=unsafe_allow_html)


def success(s, module=st, unsafe_allow_html=True):
    s = s.replace("\n", "<br>")
    module.markdown(f'<p class="success-text">{s}</p>', unsafe_allow_html=unsafe_allow_html)


def error(s, center=True, module=st, unsafe_allow_html=True):
    s = s.replace("\n", "<br>")
    module.markdown(f'<p class="error-text"' + ('' if center else 'style="text-align: left;"') + f'>{s}</p>',
                    unsafe_allow_html=unsafe_allow_html)


def info(s, center=True, module=st, unsafe_allow_html=True):
    s = s.replace("\n", "<br>")
    module.markdown(f'<p class="info-text"' + ('' if center else 'style="text-align: left;"') + f'>{s}</p>',
                    unsafe_allow_html=unsafe_allow_html)


def exception(s, module=st, unsafe_allow_html=True):
    s = s.replace("\n", "<br>")
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    s = ansi_escape.sub('', s)
    module.markdown(f'<p class="exception-text">{s}</p>', unsafe_allow_html=unsafe_allow_html)


def unsafe_md(label=None, module=st, unsafe_allow_html=True):
    if label is None:
        label = ""

    if not isinstance(label, (str, int, float)):
        label.markdown("", unsafe_allow_html=unsafe_allow_html)
    else:
        module.markdown(label, unsafe_allow_html=True)


def setup():
    st.set_page_config(layout="wide")
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewBlockContainer"] {
            padding-top: 3rem !important;
        }
        .success-text {
            padding: 10px;
            background-color: #d4edda;
            color: #155724;
            border-radius: 5px;
            text-align: center;
        }
        .error-text {
            padding: 10px;
            background-color: #f8d7da;
            color: #721c24;
            border-radius: 5px;
            text-align: center;
        }
        .info-text {
            padding: 10px;
            background-color: #1c83e11a;
            color: #004280;
            border-radius: 5px;
            text-align: center;
        }
        .pending-text {
            padding: 10px;
            background-color: #f0f2f6;
            color: #31333f;
            border-radius: 5px;
            text-align: center;
        }
        .exception-text {
            padding: 15px;
            background-color: #ff2b2b17;
            color: #7b353b;
            border-radius: 8px;
        }
        div[role="radiogroup"] {
            margin-left: 3px;
            margin-top: 10px;
        }
        button {
            height: auto;
            padding-top: 9px !important;
            padding-bottom: 9px !important;
        }
        hr {
            display: block;
            height: 1px;
            border: 0;
            border-top: 1px solid #ccc;
            margin: 0em 0;
            padding: 0;
        }
        div[data-testid=stPopoverBody] div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid=stHorizontalBlock] button {
            height: 22px;
            min-height: 22px;
            width: 60px;
            padding: 0px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        div[data-testid=stPopoverBody] div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid=stHorizontalBlock] div[data-testid="stVerticalBlockBorderWrapper"] button {
            height: 25px;
            min-height: 25px;
            min-width: 240px;
            padding: 0px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        div[data-testid=stPopoverBody] button p {
            line-height: 12px;
        }
        div[data-testid=stPopoverBody] div[data-testid=stVerticalBlock] {
            gap: 0.5rem;
        }
        .stProgress div[aria-label="100% Loaded"] div div {
            background-color: #32CD32;
        }
        div[aria-label="Generation"] span {
            font-weight: 600;
        }
        div[aria-label="Generation"] span[style="color: rgb(255, 43, 43);"] {
            color: #C70039 !important;
        }
        div[aria-label="Generation"] span[style="color: rgb(217, 90, 0);"] {
            color: #FFC300 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


COMPONENTS_CONFIGURATION = """
    <script>
    const buttons = window.parent.document.querySelectorAll('.st-emotion-cache-1umgz6k.ef3psqc12')
    buttons.forEach((x) => {
        if (['←', '→'].indexOf(x.childNodes[0].childNodes[0].childNodes[0].textContent) >= 0 )
            x.style.cssText = 'margin-top: 12px !important; padding-top: 0px !important; padding-bottom: 0px !important;'
        if (x.parentNode.parentNode.dataset.testid === "stPopover")
            x.style.cssText = 'margin-top: 12px !important; padding-top: 0px !important; padding-bottom: 0px !important;'
    })

    //const iframe = window.parent.document.querySelectorAll('iframe')[0];
    //const innerDoc = iframe.contentDocument || iframe.contentWindow.document;
    //console.log(innerDoc.querySelectorAll('div'))
    </script>
    """
