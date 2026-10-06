import os
import sys
import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import params
import gui_tools as ut

def main():
    st.set_page_config(page_title="Results", page_icon="C:\GitHub\RDR\gui\__siteIcon__ .ico")
    st.logo("C:\GitHub\RDR\gui\__siteIcon__ .ico")

    st.title("**Results**", width="content", text_alignment="justify")
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

    section_number = 16
    element_number = 0
    # ===================
    # RESULTS OVERVIEW
    # ===================
    if params.save_file.value is not None and params.save_file.value != "":
        if params.output_dir.value is not None:
            parameter = params.Param(
                name='reports', 
                title='Reports Folder', 
                desc='Automatically generated folder within the output directory containing reports.',
                dtype='fpath',
                )
            element_number += 1
            fname = "Reports"
            if os.path.exists(os.path.join(params.output_dir.value, fname)):
                parameter.value = os.path.join(params.output_dir.value, fname)
                st.session_state[parameter.name] = parameter.value

                if parameter.name in st.session_state.keys():
                    if st.session_state[parameter.name] is not None:
                        if os.path.exists(st.session_state[parameter.name]):
                            
                            filename = st.selectbox("Choose the Tableau file you would like to view.", options=[folder.name for folder in os.scandir(st.session_state["reports"]) if folder.is_dir()], key="selected_tableau_file")
                            filepath = os.path.join(parameter.value, filename, 'tableau_dashboard.twbx')

                            left, right = st.columns(2)
                            with left:
                                if st.button("View in Tableau", width='stretch', type='primary', key=parameter.name+"_view"):
                                    os.startfile(filepath)
                            with right:
                                if st.button("Go to file location", width='stretch', key=parameter.name+"_go_to_file"):
                                    os.startfile(os.path.dirname(filepath))
                            st.markdown("")
                            st.markdown("")
            else:
                st.markdown('<span style="background-color: #B10000; color: #FFFFFF">Failed to detect Reports folder in the output directory.  \nComplete an RDR run before proceeding.</span>', unsafe_allow_html=True)  

            if os.path.exists(os.path.join(params.output_dir.value, f'tableau_input_file_{params.run_id.value}.xlsx')):
                bca_tab = pd.read_excel(os.path.join(params.output_dir.value, f'tableau_input_file_{params.run_id.value}.xlsx'), sheet_name='BCA')
                selected_attribute = st.selectbox(label='Select BCA attribute', options=bca_tab.Attribute.unique())
                fig = px.bar(bca_tab.loc[bca_tab['Attribute']==selected_attribute,:], x="ProjectName", y="Value", color="Hazard")
                st.plotly_chart(fig)

                st.caption("Raw Tableau input from most recent RDR run.")
                ut.display_csv(os.path.join(params.output_dir.value, f'tableau_input_file_{params.run_id.value}.xlsx'), edit_file_allowed=False)
                if st.button("Refresh file display", icon=":material/refresh:", key="modelparams_refresh"):
                    pass

        else:
            st.markdown('<span style="background-color: #B10000; color: #FFFFFF">Failed to detect Reports folder because no output directory is set yet.  \nGo back to the General tab and set 1.2 Output Directory before proceeding.</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="background-color: #0B59F4; color: #FFFFFF">Load a save file to see results.  \nClick Load save at the top and select a save file before proceeding.</span>', unsafe_allow_html=True)



if __name__ == "__main__":
    main()