import os
import sys
import datetime
import pandas as pd
import numpy as np
import subprocess

import params
import gui_tools as ut

import streamlit as st

def main():
    st.set_page_config(page_title="Run RDR", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    st.title("**Run RDR**", width="content", text_alignment="justify")
    st.caption(f"Currently loaded: {params.save_file.value}")

    left, lmiddle, rmiddle, right = st.columns(4, gap=None)

    if left.button("Load save 📂", width="stretch", type="tertiary"):
        ut.load_save_dialog()

    if lmiddle.button("Save 💾", width="stretch", type="tertiary"):
        if params.save_file is None:
            # state_save(params.save_folder, params.save_name, param_list, go_to)
            ut.save_as_dialog()
        
        elif params.save_file.value is None or params.save_file.value == "":
            # state_save(params.save_folder, params.save_name, param_list, go_to)
            ut.save_as_dialog()

        else:
            ut.quick_save_dialog()

    if rmiddle.button("Save as 📝", width="stretch", type="tertiary"):
        ut.save_as_dialog()

    if right.button("Clear all ❌", width="stretch", type="tertiary"):
        ut.clear_all()

    not_set = False
    # ===================
    # RUN RDR
    # ===================
    section_number = 15
    st.header(f"{section_number}. :primary[Run RDR]")

    st.markdown(f"#### Batch file: {params.bat_file.value}")
    if params.bat_file.value is not None and params.bat_file.value != "":
        if os.path.exists(params.bat_file.value):
            st.session_state['inputs_reviewed'] = True
            st.session_state['inputs_validated'] = True
        else: not_set = True
    else: not_set = True

    st.markdown(f"#### Loaded save file: {params.save_file.value}")
    if params.save_file.value is None or params.save_file.value == "":
        not_set = True
    st.markdown(f"#### Inputs reviewed: {st.session_state['inputs_reviewed'] if 'inputs_reviewed' in st.session_state.keys() else False}")
    st.markdown(f"#### Inputs validated: {st.session_state['inputs_validated'] if 'inputs_validated' in st.session_state.keys() else False}")

    if not_set:
        st.markdown(f'<span style="background-color: #B10000; color: #FFFFFF">Cannot run RDR if any parameters above are missing values.</span>', unsafe_allow_html=True)


    if st.button("Configuration is correct ✅", width="stretch", key="confirm_button", disabled=not_set):
        pass

    if st.button("Run RDR", width="stretch", type="primary", disabled=not(st.session_state.confirm_button)):
        with st.spinner("###### Running RDR... check your terminal window for the logger", show_time=True, width="stretch"):
            subprocess.run(params.bat_file.value)
            st.success("Done. Check logger for errors.")

if __name__ == "__main__":
    main()