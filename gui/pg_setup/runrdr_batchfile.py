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

        
    # Adapted with permission from the Freight and Fuel Transportation Optimization Tool https://github.com/VolpeUSDOT/FTOT-Public
    # ===================
    # BATCH FILE
    # ===================
    section_number = 14
    element_number = 0
    st.header(f"{section_number}. Generate the :primary[Batch File]")
    not_set = False
    not_set_list = []

    if params.bat_file.value is not None and params.bat_file.value != "":
        parameter = params.bat_file
        element_number = 1
        st.session_state[parameter.name] = parameter.value
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name, disabled=True)
        ut.create_display_echo(parameter)
        if parameter.value is None or parameter.value == "":
            not_set = True
            not_set_list.append(parameter.title)

    if params.bat_file.value is None or not os.path.exists(params.bat_file.value):
        st.markdown(f'<span style="background-color: #B10000; color: #FFFFFF">Batch file does not exist at location specified or has not been created yet.</span>', unsafe_allow_html=True)
        # Batch file location
        parameter = params.bat_location
        element_number = 2
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
        if parameter.value is None or parameter.value == "":
            not_set = True
            not_set_list.append(parameter.title)

    # Input dir
    parameter = params.input_dir
    if parameter.value is None or parameter.value == "":
        section_number = 1
        element_number = 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        ut.input_dir_text_input(display, parameter)
        ut.create_display_echo(parameter)
    if parameter.value is None or parameter.value == "":
        not_set = True
        not_set_list.append(parameter.title)

    # Run ID
    parameter = params.run_id
    if parameter.value is None or parameter.value == "":
        section_number = 1
        element_number = 3
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
    if parameter.value is None or parameter.value == "":
        not_set = True
        not_set_list.append(parameter.title)

    # Python installation location
    parameter = params.python
    if parameter.value is None or parameter.value == "":
        section_number = 6
        element_number = 1
        forced_default = sys.executable
        if parameter.value is None:
            parameter.value = forced_default
        parameter_entry_disabled = True
        if st.button(f"Edit {parameter.title} (Not Recommended)", width='stretch', type='primary'):
            parameter_entry_disabled = not parameter_entry_disabled
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, disabled=parameter_entry_disabled, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
    if parameter.value is None or parameter.value == "":
        not_set = True
        not_set_list.append(parameter.title)

    # RDR program directory
    parameter = params.rdr
    if parameter.value is None or parameter.value == "":
        section_number = 6
        element_number = 3
        parameter_entry_disabled = True
        if st.button(f"Edit {parameter.title} (Not Recommended)", width='stretch', type='primary'):
            parameter_entry_disabled = not parameter_entry_disabled
        element_number += 1
        display = ut.create_display_name(parameter, section=section_number, element=element_number)   
        st.text_input(display, value=parameter.value, disabled=parameter_entry_disabled, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        ut.create_display_echo(parameter)
    if parameter.value is None or parameter.value == "":
        not_set = True
        not_set_list.append(parameter.title)

    # # Second half: non-config filepaths
    # # Move non-config files to correct locations
    # if st.button("Copy RDR files to their correct locations", width="stretch", disabled=True):
    #     ut.move_non_config_files(input_dir = params.input_dir.value, 
    #                                 haz = params.hazards, 
    #                                 ecf = params.economic_futures, 
    #                                 net = params.network_links, 
    #                                 nwn = params.net_node, 
    #                                 pri = params.proj_info, 
    #                                 prt = params.proj_table)
    #     st.markdown('Hazards, AEMaster, Networks, and LookupTables directories successfully created and associated files copied. Starting batch file creation...')

    if not_set:
        st.markdown(f'<span style="background-color: #B10000; color: #FFFFFF">Cannot generate batch file because no {", ".join(not_set_list)} set.  \nSet value(s) for the listed parameter(s) before proceeding.</span>', unsafe_allow_html=True)

    if params.bat_file.value is None or params.bat_file.value == "" or not os.path.exists(params.bat_file.value):
        if st.button("Generate batch file", width="stretch", type="primary", disabled=not_set, key='generate_batch_button'):
                run_bat_file = ut.create_bat(python = params.python.value, rdr = params.rdr.value, bat_location = params.bat_location.value, run_id = params.run_id.value, save_file = params.save_file.value)
                params.bat_file.value = run_bat_file
                st.markdown("Batch file saved to: {}".format(run_bat_file))
                ut.quick_save_dialog()


    disabled = True
    if params.bat_file.value is not None and params.bat_file.name != "":
        if os.path.exists(params.bat_file.value):
            disabled = False
    l, r = st.columns([8, 8])
    with r:
        if st.button(":gray[__Batch file generated. Continue to Run RDR__ ►]" if disabled else ":green[__Batch file generated. Continue to Run RDR__ ►]", 
                     type='tertiary', 
                     disabled=disabled):           
            st.switch_page("pg_setup/runrdr_runrdr.py")

if __name__ == "__main__":
    main()