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

    # ===================
    # REVIEW CONFIGURATION
    # ===================
    section_number = 12
    st.header(f"{section_number}. :primary[Review] the Configuration")

    st.caption("General Configuration")

    st.data_editor(
        pd.DataFrame(
            {"name":[x.refnum + " " + x.title for x in params.param_list], "value":[str(x.value) for x in params.param_list]}
        ), column_config={
            "name": st.column_config.TextColumn(
                "Parameter Name",
                help="The unique name of the parameter",
                width="medium",
                disabled=True,
                required=True
            ),
            "value": st.column_config.TextColumn(
                "Parameter Value",
                help="The value set to the parameter named at left",
                width="large",
                default=params.input_dir.value,
                disabled=True,
                required=True
            )

        }, num_rows="fixed", key="hazards_table_editing_info"
    )

    st.caption("Model Parameters")
    ut.display_csv(params.mod_fpath)

    l, r = st.columns([7, 8])
    disabled = False
    if params.save_file.value is None or params.save_file.value == "":
        disabled = True
    with r:
        if st.button(":gray[__Inputs reviewed. Continue to Validation__ ►]" if disabled else ":green[__Inputs reviewed. Continue to Input Validation__ ►]", 
                     type='tertiary', 
                     disabled=disabled):
            st.session_state["inputs_reviewed"] = True            
            st.switch_page("pg_setup/runrdr_inputvalidation.py")


    # st.markdown("### Hazards")
    # ut.display_csv(params.haz_folder)

    # st.markdown("### Projects")
    # ut.display_csv(params.lookuptables_folder)

    # st.markdown("### Network")
    # ut.display_csv(params.networks_folder)

if __name__ == "__main__":
    main()