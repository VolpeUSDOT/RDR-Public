import os
import sys
import argparse

import params
import gui_tools as ut

import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'helper_tools', 'input_validation'))
import rdr_input_validation as iv

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

    # ===================
    # INPUT VALIDATION
    # ===================
    section_number = 13
    st.header(f"{section_number}. Input :primary[Validation]")

    not_set = False

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

    if params.bat_file.value is not None and params.bat_file.value != "":
        if os.path.exists(params.bat_file.value):
            st.session_state['inputs_reviewed'] = True
    disabled = True
    st.markdown(f"#### Loaded save file: {params.save_file.value}")
    if params.save_file.value is None or params.save_file.value == "":
        not_set = True
    st.markdown(f"#### Inputs reviewed: {st.session_state['inputs_reviewed'] if 'inputs_reviewed' in st.session_state.keys() else False}")

    if not_set:
        st.markdown(f'<span style="background-color: #B10000; color: #FFFFFF">Cannot validate inputs if any parameters above are missing values.</span>', unsafe_allow_html=True)


    if st.button("Validate inputs", width="stretch", type="primary", disabled=not_set):
        with st.spinner("###### Validating inputs... check your terminal window for the logger", show_time=True, width="stretch"):
            iv_args = argparse.ArgumentParser()
            iv_args.add_argument('--input_validation')
            iv_args.add_argument('--config_file')
            args = iv_args.parse_args(['--input_validation', 
                                os.path.join(os.path.dirname(__file__), '..', '..', 'helper_tools', 'input_validation', 'rdr_input_validation.py'),
                                '--config_file',
                                params.save_file.value])
            iv.main(args)
            st.success("Done. Check input validation logger for errors.")

    if params.bat_file.value is not None and params.bat_file.value != "":
        disabled = False
    l, r = st.columns([9, 8])
    with r:
        if st.button(":gray[__Inputs validated. Continue to Batch File__ ►]" if disabled else ":green[__Inputs validated. Continue to Batch File__ ►]", 
                     type='tertiary', 
                     disabled=disabled):
            st.session_state["inputs_validated"] = True       
            st.switch_page("pg_setup/runrdr_batchfile.py")

if __name__ == "__main__":
    main()