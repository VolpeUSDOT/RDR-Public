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

    # ===================
    # MODEL PARAMETERS
    # ===================
    section_number = 7
    st.header(f"{section_number}. :primary[Model] Parameters")
    st.html(
        """
        Contains user parameters for:
        <br>(1) each economic scenario,
        <br>(2) each trip loss elasticity,
        <br>(3) the project group membership for each project,
        <br>(4) each hazard name, filename, dimensions, desciption, and event probability,
        <br>(5) the recovery stages,
        <br>(6) and the event frequency factors.
        <br>
        <br>
        """)
    element_number = 0
    parameter = params.mod_fpath
    element_number += 1
    fname = "Model_Parameters.xlsx"
    # if st.button("Auto-detect Model_Parameters.xlsx file", key="mod_detect_button"):
    if params.input_dir.value is not None:
        if parameter.value is None or parameter.value == "":
            st.session_state[parameter.name] = None
            if os.path.exists(os.path.join(params.input_dir.value, fname)):
                parameter.value = os.path.join(params.input_dir.value, fname)
                st.session_state[parameter.name] = parameter.value
    else:
        st.markdown('<span style="background-color: #B10000; color: #FFFFFF">Failed to detect file because no input directory is set yet.  \nGo back to the General tab and set 1.1 Input Directory before proceeding.</span>', unsafe_allow_html=True)
    display = ut.create_display_name(parameter, section=section_number, element=element_number)   
    st.text_input(display, value=parameter.value, key=parameter.name)
    parameter.value = st.session_state[parameter.name]
    ut.create_display_echo(parameter)

    template_location = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "Model_Parameters.xlsx")
    ut.display_csv(parameter, template_location = template_location, create_file_location = fname)
    if st.button("Refresh file display", icon=":material/refresh:", key="modelparams_refresh"):
        pass

if __name__ == "__main__":
    main()