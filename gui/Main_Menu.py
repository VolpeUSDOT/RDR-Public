import os
import sys
import datetime
import pandas as pd
import numpy as np
import params
import streamlit as st

import gui_tools as ut

def main_menu():
    st.markdown("""
                # Resilience and Disaster Recovery (RDR) Tool Suite
                
                """)

    left, middle, right = st.columns(3, vertical_alignment="center")
    left.markdown("Load an RDR save file")
    if middle.button("Load Save 📂", width="stretch"):
        ut.load_save_dialog()

    left, middle, right = st.columns(3, vertical_alignment="center")
    left.markdown("Configure your RDR run")
    if middle.button("Set RDR Parameters", width="stretch"):
        st.switch_page("pg_parameters/parameters_general.py")

    left, middle, right = st.columns(3, vertical_alignment="center")
    left.markdown("Execute your RDR run")
    if middle.button("Run RDR", width="stretch"):
        st.switch_page("pg_setup/runrdr_review.py")

    left, middle, right = st.columns(3, vertical_alignment="center")
    left.markdown("Go to the documentation")
    if middle.button("Help", width="stretch"):
        st.switch_page("pg_help_about/help.py")

    left, middle, right = st.columns(3, vertical_alignment="center")
    left.markdown("Description and contact info")
    if middle.button("About", width="stretch"):
        st.switch_page("pg_help_about/about.py")

def main():
    st.set_page_config(page_title="RDR Main Menu", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    pg_main_menu = st.Page(main_menu, title="Main Menu")
    
    # pg_setparameters = st.Page("pg_parameters/parameters_setparameters.py", title="Set Parameters")
    pg_general = st.Page("pg_parameters/parameters_general.py", title="General")
    pg_model = st.Page("pg_parameters/parameters_model.py", title="Model")
    pg_hazards = st.Page("pg_parameters/parameters_hazards.py", title="Hazards")
    pg_projects = st.Page("pg_parameters/parameters_projects.py", title="Projects")
    pg_network = st.Page("pg_parameters/parameters_network.py", title="Network")
    pg_matrices = st.Page("pg_parameters/parameters_matrices.py", title="Matrices")
    
    pg_review = st.Page("pg_setup/runrdr_review.py", title="Review")
    pg_inputvalidation = st.Page("pg_setup/runrdr_inputvalidation.py", title="Validation")
    pg_batchfile = st.Page("pg_setup/runrdr_batchfile.py", title="Batch File")
    pg_runrdr = st.Page("pg_setup/runrdr_runrdr.py", title="Run RDR")
    
    pg_help = st.Page("pg_help_about/help.py", title="Help")
    pg_about = st.Page("pg_help_about/about.py", title="About")

    pg_results = st.Page("pg_results/results_overview.py", title = "Overview")

    pages = st.navigation(
        {
            "RDR": [pg_main_menu],
            "Parameters": [pg_general, pg_model, pg_hazards, pg_projects, pg_network, pg_matrices],
            "Run RDR": [pg_review, pg_inputvalidation, pg_batchfile, pg_runrdr],
            "Results": [pg_results],
            "Help and About": [pg_help, pg_about],

        }
    )

    pages.run()

if __name__ == "__main__":
    main()