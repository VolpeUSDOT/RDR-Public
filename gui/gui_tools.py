# Helper tools for RDR UI
import os
import json
import shutil
from pathlib import Path
from typing import Union

import streamlit as st

# import ui
from params import dtypes, param_list, shorts, shorts_multi, MultiParam, Param
import params
import gui_validation as gv

import pandas as pd

def strip_surrounding_quotes(value: str | None) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if len(stripped) >= 2 and stripped[0] in ('"', "'") and stripped[-1] == stripped[0]:
            return stripped[1:-1]
    return value

def input_dir_text_input(display: str, parameter: Param) -> None:
    def normalize_input_dir_state():
        st.session_state[parameter.name] = strip_surrounding_quotes(st.session_state[parameter.name])

    if parameter.name in st.session_state:
        normalize_input_dir_state()
    st.text_input(display, value=parameter.value, key=parameter.name, on_change=normalize_input_dir_state)
    parameter.value = strip_surrounding_quotes(st.session_state[parameter.name])

def clean_input():
    pass

def create_display_name(parameter: Param, section: int = "", element: int = "", set_refnum: bool = True) -> str:
    # Initialize required, which will be set to a red star if the parameter is required 
    required = ""
    # Initialize the info icon, which will be set to material/Info if the parameter has a description
    info_icon = ""
    if parameter.required:
        required = ":red[*] "
    if parameter.desc != "":
        info_icon = "\u2000  \n:material/Info:"
    # Write the reference number in section.element format to the parameter's refnum property
    # Unless the refnum already exists
    if set_refnum:
        parameter.refnum = f"{section}.{element}"
    # Return the string to be printed as the input box's caption
    return required + parameter.refnum + " __" + parameter.title + "__" + info_icon + parameter.desc + ""

def create_display_echo(parameter: Param) -> str:
    if parameter.dtype in ['int', 'float', 'year']:
        return st.code(f"{parameter.name}: {parameter.value}")
    if parameter.value is None:
        return st.code(f"{parameter.name}: {parameter.value}")
    return st.code(f"{parameter.name}: '{parameter.value}'")

def display_csv(parameter: Param | str, create_display: bool = False, template_location: str = "", create_file_location: str = "", detector: str = "", create_file_allowed: bool = True, edit_file_allowed: bool = True) -> None:
    """Creates the CSV/XLSX display and handles file creation where file is missing.

    :param parameter: The CSV/XLSX filename parameter from params.py.
    :param create_display: Create the parameter display and entry pane for the parameter along with the CSV/XLSX display.
    :param template_location: The path to the template file if one exists.
    :param create_file_location: The path within the input dir where a file needs to be create.
    :return: None.
    """
    if isinstance(parameter, str):
        parameter = Param(os.path.basename(parameter)+"_temp", dtype="path", value=parameter)
    fnf = False
    if create_display:
        display = create_display_name(parameter, set_refnum=False)   
        st.text_input(display, value=parameter.value, key=parameter.name)
        parameter.value = st.session_state[parameter.name]
        create_display_echo(parameter)

    if parameter.value is None:
        st.markdown(f"{parameter.refnum} {parameter.title} is empty or invalid currently. When a file path is set, its contents will be displayed here.")
        fnf = True
    elif parameter.value == "":
        st.markdown(f"{parameter.refnum} {parameter.title} is empty or invalid currently. When a file path is set, its contents will be displayed here.")
        fnf = True
    elif not os.path.exists(parameter.value):
        st.markdown(f"File not found for {parameter.refnum} {parameter.title} at the location specified. When a file path is set, its contents will be displayed here.")
        fnf = True
    
    if fnf and create_file_allowed:
        if st.button("Create file", type='primary', width='stretch', key=parameter.name+"_create_file"):
            if params.input_dir.value is not None:
                copy_location = os.path.join(params.input_dir.value, create_file_location)
                shutil.copy(template_location, copy_location)
                parameter.value = copy_location
            else:
                if params.input_dir.value is None or params.input_dir.value == "":
                    st.markdown("Failed to create file because no input directory is set yet.  \nGo back to the General tab and set parameter 1.1 Input Directory before proceeding.")
            st.markdown("File successfully created. If the file has an associated auto-detect button, click it to load in the file.")
        return

    if edit_file_allowed:
        left, right = st.columns(2)
        with left:
            if st.button("Edit in default application", width='stretch', type='primary', key=parameter.name+"_edit"):
                os.startfile(parameter.value)
        with right:
            if st.button("Go to file location", width='stretch', key=parameter.name+"_go_to_file"):
                os.startfile(os.path.dirname(parameter.value))

    ext = os.path.splitext(parameter.value)[1]      
    if ext == ".csv":
        show = pd.read_csv(parameter.value, nrows=100000).reset_index(drop=True)
        show.index += 1
        st.caption(os.path.basename(parameter.value))
        st.data_editor(
            show, 
            num_rows="fixed", 
            disabled=True,
            width='content',
            key=f"{parameter.name}_table_editing_info"
        )
        return
    if ext == ".xlsx":
        for sheet in pd.ExcelFile(parameter.value).sheet_names:
            if sheet == "Instructions":
                continue
            show = pd.read_excel(open(parameter.value, "rb"), sheet_name=sheet).reset_index(drop=True)
            show.index += 1
            st.caption(sheet)
            st.data_editor(
                show, 
                num_rows="fixed",
                disabled=True,
                width='content',
                key=f"{parameter.name}_{sheet}_table_editing_info"
            )
        return
    st.markdown(f"File for {parameter.refnum} {parameter.title} needs to be a .csv or a .xlsx file.")
    return   


def write_bat(python: str, rdr: str, run_bat_file: str, save_file: str) -> None:
    # Adapted with permission from the Freight and Fuel Transportation Optimization Tool https://github.com/VolpeUSDOT/FTOT-Public
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(python))), 'Scripts')
    
    with open(run_bat_file, 'w') as wf:
        st.markdown("Writing the file: {}".format(run_bat_file))

        # Batch file content
        content = """

        @ECHO OFF
        cls
        set PYTHONDONTWRITEBYTECODE=1
        REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
        REM   for debugging REM @ECHO OFF line above to see commands
        REM -------------------------------------------------


        REM ==============================================
        REM ======== ENVIRONMENT VARIABLES ===============
        REM ==============================================
        set PATH={};%PATH%
        set PYTHON={}
        set RDR={}

        set CONFIG={}

        call activate RDRenv
        cd C:\GitHub\RDR\metamodel_py


        REM ==============================================
        REM ======== RUN THE RDR SCRIPT ==================
        REM ==============================================

        REM lhs: select AequilibraE runs needed to fill in for TDM
        %PYTHON% %RDR% %CONFIG% lhs
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM aeq_run: use AequilibraE to run core model for runs identified by LHS
        %PYTHON% %RDR% %CONFIG% aeq_run
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM aeq_compile: compile all AequilibraE run results
        %PYTHON% %RDR% %CONFIG% aeq_compile
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM rr: run regression module
        %PYTHON% %RDR% %CONFIG% rr
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM recov_init: read in input files and extend scenarios for recovery process
        %PYTHON% %RDR% %CONFIG% recov_init
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM recov_calc: consolidate metamodel and recovery results for economic analysis
        %PYTHON% %RDR% %CONFIG% recov_calc
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM o: summarize and write output
        %PYTHON% %RDR% %CONFIG% o
        if %ERRORLEVEL% neq 0 goto ProcessError

        REM test: use to test methods under development
        REM %PYTHON% %RDR% %CONFIG% test
        REM if %ERRORLEVEL% neq 0 goto ProcessError

        call conda.bat deactivate
        pause
        exit /b 0

        :ProcessError
        REM error handling: st.markdown message and clean up
        echo ERROR: RDR run encountered an error. See above messages (and log files) to diagnose.

        call conda.bat deactivate
        pause
        exit /b 1
        """.format(script_path, python, rdr, save_file)
        wf.writelines(content.replace("        ", ""))  # remove the indentation white space

def create_bat(python: str, rdr: str, bat_location: str, run_id: str, save_file: str) -> str:
    # Adapted with permission from the Freight and Fuel Transportation Optimization Tool https://github.com/VolpeUSDOT/FTOT-Public

    run_bat_file = os.path.join(bat_location, "run_rdr_{}.bat".format(run_id))

    n = 1
    while os.path.exists(run_bat_file):
        run_bat_file = os.path.join(bat_location, "run_rdr_{}_{}.bat".format(run_id, n))
        n += 1
    
    write_bat(python, rdr, run_bat_file, save_file)

    return run_bat_file

@st.dialog("Quick save")
def quick_save_dialog():
    quick_save(save_file=params.save_file, param_list=params.param_list)
    st.write("Saved")

def quick_save(save_file: Param, param_list: list, go_to: str = 'sequential') -> None:

    save_dict = save_params(param_list, go_to)
    with open(save_file.value, 'w', encoding = 'utf-8') as save_state:  # https://stackoverflow.com/a/12309296
        json.dump(save_dict, save_state, ensure_ascii = False)    

@st.dialog("Save as")
def save_as_dialog():
    # params.save_folder.value = os.path.join(os.path.dirname(__file__), "saves")
    params.save_name.value = st.text_input("Save file name", value=params.save_name.value, key="save_name")
    l, r = st.columns(2)
    with l:
        if st.button("Save 💾", width="stretch"):
            state_save(save_folder = params.save_folder.value, save_name = params.save_name.value, param_list = params.param_list, go_to = 'sequential')
            st.rerun()
    with r:
        if st.button("Cancel", width="stretch", type="primary"):
            st.rerun()

def state_save(save_folder: str, save_name: str, param_list: list, go_to: str = 'sequential') -> None:
    # if save_folder is None or save_name is None:
    #     save_as_dialog()
    save_folder = save_folder.strip(' "').strip(" '")
    save_name = save_name.strip(' "').strip(" '")

    params.save_file.value = os.path.join(save_folder, save_name + ".save")
    save_dict = save_params(param_list, go_to)

    with open(params.save_file.value, 'w', encoding = 'utf-8') as save_state:  # https://stackoverflow.com/a/12309296
        json.dump(save_dict, save_state, ensure_ascii = False)

def save_params(param_list: list, go_to: str) -> dict:
    save_dict = {'go_to': go_to}

    for parameter in param_list:
        if parameter.mval is None:
            save_dict[parameter.short] = parameter.value
        else:
            save_dict[parameter.short] = [multi.attributes() for multi in parameter.mval]

    return save_dict

@st.dialog("Load save 📂")
def load_save_dialog():
    filename = st.selectbox("Choose the save file you would like to load", options=os.listdir(os.path.join(os.path.dirname(__file__), "saves")), key="save_folder")
    save_file = os.path.join(os.path.dirname(__file__), "saves", filename)
    l, r = st.columns(2)
    with l:
        if st.button("Load", width="stretch"):
            st.session_state.clear()
            params.save_file.value, go_to = load_save(save_file = save_file, param_list = params.param_list)
            st.rerun()
    with r:
        if st.button("Cancel", width="stretch", type="primary"):
            st.rerun()
            
def load_save(save_file: str, param_list: list) -> str:
    user_input = save_file.strip('" ').strip("' ")

    with open(user_input) as save_state:  # https://stackoverflow.com/a/20199213
        save_dict = json.load(save_state)

    for short in save_dict.keys():  # https://stackoverflow.com/a/7125547
        for parameter in param_list:
            if parameter.short == short:
                if parameter.short in shorts_multi:
                    mval = []
                    for mparam in save_dict[short]:
                        temp = MultiParam()
                        temp.write_attributes(mparam)
                        mval.append(temp)
                    parameter.mval = mval
                    break
                parameter.value = strip_surrounding_quotes(save_dict[short]) if parameter is params.input_dir else save_dict[short]
                st.session_state[parameter.name] = parameter.value
                break

    return user_input, save_dict['go_to']

@st.dialog("Clear all values", dismissible=False)
def clear_all():
    st.markdown("Are you sure you want to clear all entered values?")
    # st.markdown("***You may need to reload your browser page to clear all values.***")
    # st.markdown("""*This functionality is currently under construction.
    #             Values will be cleared from your session, but the values entered
    #             into user input fields like textboxes and buttons will persist
    #             despite no longer existing in the session. To fully clean out all
    #             input fields, reload your browser page.*""")

    l, r = st.columns(2)
    disabled = False
    if l.button("Clear all ❌", width='stretch', type='secondary', key = 'clearall'):
        pass
    if st.button("Confirm clear all ❌", width='stretch', type='secondary', disabled=not(st.session_state['clearall'])):
        params.save_file.value = None
        for value, parameter in zip(params.values, params.param_list):
            parameter.value = value
        st.session_state.clear()
        # Force reload the browser (from https://discuss.streamlit.io/t/force-reload-of-webpage/43793/3)
        # streamlit_js_eval(js_expressions="parent.window.location.reload(true)")
        st.markdown("Reload the page to complete clearing all. Failing to reload the page will cause the Clear all ❌ process to not complete.")
        disabled = True
    with r:
        if st.button("Cancel", width="stretch", type="primary", disabled=disabled):
            st.rerun()


# def build_input(param: Param, message: str = '', info: str = '', **kwargs) -> Union[str, float, int, bool, None]:
#     dtype = param.dtype
    
#     if dtype == 'multi':
#         if len(param.mval) > 0:
#             mnames = [x.name for x in param.mval]
#             st.markdown('\nParameter name: {}\nNumber of items: {}\nItem name(s)   : {}\nShortcut      : {}'.format(param.name, len(param.mval), mnames, param.short))

#             return ask_multi(param, message, info, mlist = kwargs['mlist'])

#         st.markdown('\nParameter name: {}\nCurrent value: {}\nShortcut      : {}'.format(param.name, param.value, param.short))
#         return ask_multi(param, message, info, mlist = kwargs['mlist'])
    
#     st.markdown('\nParameter name: {}\nCurrent value: {}\nShortcut      : {}'.format(param.name, param.value, param.short))
#     if dtype == 'path':
#         return ask_path(message, fn_or_dir = kwargs['fn_or_dir'], should_exist = kwargs['should_exist'])

#     if dtype in ['year', 'int', 'float']:
#         return ask_num(message, dtype, low = kwargs['low'], high = kwargs['high'])

#     if dtype == 'str':
#         return ask_string(message, char_floor = kwargs['char_floor'], char_ceiling = kwargs['char_ceiling'], illegal_chars = kwargs['illegal_chars'])
    
#     if dtype == 'options':
#         if param.options is None:
#             raise Exception('DEV ERROR: dtype of {} is options. options type params must have a list in its options argument at instantiation.'.format(param.name))
#         return ask_options(message, options = param.options)

#     raise Exception('DEV ERROR: dtype of {} not set to one of the accepted dtypes. Current dtype is {}. Change dtype or design new interaction for the new dtype.'.format(param.name, param.dtype))

def overwrite_dir(dir: str) -> str:
    """Creates and, if needed, overwrites a child directory in the parent directory (parent_dir) matching child directory name (child_dir_name)
    Returns the full child directory path. See https://stackoverflow.com/a/11660641 for code for overwriting existing folders"""
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)

    return(dir)

def copy_files(source_files: list, destination_dir: str, names: str = None) -> None:
    """Copies files from a list of source files (source_files) to a destination directory (destination_dir).
    See https://geeksforgeeks.org/python-shutil-copy-method/ for documentation on shutil copy and error catching.
    See https://stackoverflow.com/a/8384838 for extracting file names from paths."""
    n = 0
    for file in source_files:
        if names is None:
            name = os.path.basename(file)
        else:
            name = names[n]
            n += 1
        dest = os.path.join(destination_dir, name)
        if os.path.exists(dest):
            st.markdown('WARNING: {} exists and will be\noverwritten with {}.\nMove it to avoid overwriting. Identical files will not be overwritten and can be left in place.\nPress Enter key to continue...'.format(dest, file))
            # ui.universal_commands(uinput)
        try:
            shutil.copy(file, dest)
        except shutil.SameFileError:
            st.markdown('WARNING: {} has same source and destination. File not copied.'.format(file))

def move_non_config_files(input_dir: Param, haz: Param, ecf: Param, net: Param, nwn: Param, pri: Param, prt: Param) -> None:
    # TODO: move non-config files to correct locations (or verify locations?)
    # TODO: add initial year core model runs file
    # See https://stackoverflow.com/a/52774612 for moving files in Python
    # See https://stackoverflow.com/a/1274465 for creating dirs in Python

    # Check to make sure all files listed exist
    ncf_params = [haz, ecf, net]
    oth_params = [nwn, pri, prt]
    error_files = []
    error_params = []
    for param in ncf_params:
        for multi in param.mval:
            if os.path.exists(str(multi.fpath)):
                continue
            else:
                error_files.append('Name: {}, Shortcut: {}, File: {}'.format(param.name, param.short, multi.fpath))
                error_params.append(param)
    for param in oth_params:
        if os.path.exists(str(param.value)):
            continue
        else:
            error_files.append('Name: {}, Shortcut: {}, File: {}'.format(param.name, param.short, param.value))
            error_params.append(param)        

    if len(error_files) > 0:
        st.markdown('\n\n    The following files associated with the listed parameter could not be located:{}'.format('\n    '.join(error_files)))
        uinput = input('\n\n    Please note these parameters and correct their settings in SET PARAMETERS.\n    Press Enter to be redirected to SET PARAMETERS page...')
        # ui.universal_commands(uinput)
        # ui.universal_commands('-{}'.format(error_params[0].short))
        
        return  # Function breakpoint in case somehow the universal commands doesn't catch the user
    
    # Create the Hazards, AEMaster, Networks, and LookupTables folders if they don't exist
    haz_dir = os.path.join(input_dir, 'Hazards')
    if not os.path.exists(haz_dir):
        overwrite_dir(haz_dir)
    aem_dir = os.path.join(input_dir, 'AEMaster')
    if not os.path.exists(aem_dir):
        overwrite_dir(aem_dir)
    mat_dir = os.path.join(aem_dir, 'matrices')
    if not os.path.exists(mat_dir):
        overwrite_dir(mat_dir)
    net_dir = os.path.join(input_dir, 'Networks')
    if not os.path.exists(net_dir):
        overwrite_dir(net_dir)
    prj_dir = os.path.join(input_dir, 'LookupTables')
    if not os.path.exists(prj_dir):
        overwrite_dir(prj_dir)

    # Copy files
    # TODO: auto rename hazards, omx files (ecf), and lookup tables (hard-coded renaming)
    haz_files = [item.fpath for item in haz.mval]
    ecf_files = [item.fpath for item in ecf.mval]
    net_files = [item.fpath for item in net.mval]
    nwn_file = [nwn.value]
    pri_file = [pri.value]
    prt_file = [prt.value]

    # File names
    # TODO: hazard files do not necessarily have to be named by hazard name
    haz_names = [item.name + '.csv' for item in haz.mval]
    ecf_names = [item.name + '.omx' for item in ecf.mval]
    # TODO: add net_names
    nwn_name = ['node.csv']
    pri_name = ['project_info.csv']
    prt_name = ['project_table.csv']

    # Hazards (HAZ)
    copy_files(haz_files, haz_dir, haz_names) 

    # Econ futures (ECF)
    copy_files(ecf_files, mat_dir, ecf_names)

    # Network links (NET)
    copy_files(net_files, net_dir)

    # Network node (NWN)
    copy_files(nwn_file, net_dir, nwn_name)

    # Project table (PRT)
    copy_files(prt_file, prj_dir, prt_name)

    # Project info (PRI)
    copy_files(pri_file, prj_dir, pri_name)

def build_page(include):
    # TODO: wrap groups of build_input from set_params.py into the build_page function if deemed useful
    pass
