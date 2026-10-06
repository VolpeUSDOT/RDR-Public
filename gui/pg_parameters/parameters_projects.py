import os
import sys
import datetime
import pandas as pd
import numpy as np
import params
import streamlit as st

import gui_tools as ut

def main():
    st.set_page_config(page_title="RDR Parameters", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    st.title("**Parameters**", width="content", text_alignment="justify")
    st.caption(f"Currently loaded: {params.save_file.value}")

    params.save_folder.value = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")

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

    section_number = 9 
    # ===================
    # PROJECT
    # ===================

    st.header(f"{section_number}. Resilience :primary[Projects]")
    st.html(
        """
        Contains user parameters for:
        <br>(1) each resilience project as generally defined in the model parameters.
        """)
    element_number = 0
    # with st.expander("I have an RDR-compatible LookupTables folder"):
    parameter = params.lookuptables_folder
    element_number += 1
    fname = "LookupTables"
    if params.input_dir.value is not None:
        if parameter.value is None or parameter.value == "":
            st.session_state[parameter.name] = None
            if os.path.exists(os.path.join(params.input_dir.value, fname)):
                parameter.value = os.path.join(params.input_dir.value, fname)
                st.session_state[parameter.name] = parameter.value
    else:
        st.markdown('<span style="background-color: #B10000; color: #FFFFFF">Failed to detect folder because no input directory is set yet.  \nGo back to the General tab and set 1.1 Input Directory before proceeding.</span>', unsafe_allow_html=True)
    display = ut.create_display_name(parameter, section=section_number, element=element_number)   
    st.text_input(display, value=parameter.value, key=parameter.name)
    parameter.value = st.session_state[parameter.name]
    ut.create_display_echo(parameter)

    if parameter.name in st.session_state.keys():
        if st.session_state[parameter.name] is not None:
            if os.path.exists(st.session_state[parameter.name]):
                
                filename = "project_info.csv"
                filepath = os.path.join(parameter.value, filename)
                ut.display_csv(filepath)
                filename = "project_table.csv"
                filepath = os.path.join(parameter.value, filename)
                ut.display_csv(filepath)
                if st.button("Refresh file display", icon=":material/refresh:", key="projects_refresh"):
                    pass
    # with st.expander("I do not have a LookupTables folder, but I do have RDR-compatible project files"):

    # with st.expander("I do not have RDR-compatible project files"):

if __name__ == "__main__":
    main()