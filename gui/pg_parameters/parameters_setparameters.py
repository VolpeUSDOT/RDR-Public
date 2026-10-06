import os
import sys
import datetime
import pandas as pd
import numpy as np
import params
import streamlit as st

import gui_tools as ut

import Main_Menu as mm

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

    # st.pills("",[mm.main.pg_general, mm.main.pg_model, mm.main.pg_hazards, mm.main.pg_projects, mm.main.pg_network, mm.main.pg_matrices])

    st.markdown("This is where you configure the RDR parameters. This landing page is under construction.")

if __name__ == "__main__":
    main()