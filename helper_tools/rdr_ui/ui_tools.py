# Helper tools for RDR UI
import os
import json
import shutil
from pathlib import Path
from typing import Union

import ui
from params import dtypes, param_list, shorts, shorts_multi, MultiParam, Param
import params
import set_params as sp

def clean_input():
    pass

def ask_y_n(message: str) -> str:
    print(message)
    user_input = input('Enter Y or N\n   >>')
    ui.universal_commands(user_input)

    if user_input.lower() == 'y':
        return_value = 'Y'
    elif user_input.lower() == 'n':
        return_value = 'N'
    else:
        os.system('cls')
        print('Invalid input')
        ask_y_n(message)

    # returns 'Y' or 'N'
    return return_value

# TODO: should this have option to create directory if not exists (or overwrite file if exists)?
def ask_path(message: str = '', fn_or_dir: str = 'filename', should_exist: bool = True) -> str:
    # TODO: add quote stripping
    print(message)
    user_input = input('Enter a {} (drag and drop from File Explorer is fine)\n   >>'.format(fn_or_dir))
    ui.universal_commands(user_input)

    if user_input == '':
        return user_input
    
    user_input = user_input.strip("'")
    user_input = user_input.strip('"')

    # the path should be a filename if that is specified in fn_or_dir of the param, same for directory
    # this only checks if the path actually exists
    if os.path.isdir(user_input) and fn_or_dir == 'filename':
        print("Invalid entry. Enter a file path instead of a directory (folder) path.")
        ask_path(message, fn_or_dir, should_exist)
    elif os.path.isfile(user_input) and fn_or_dir == 'directory':
        print("Invalid entry. Enter a directory (folder) path instead of a file path.")
        ask_path(message, fn_or_dir, should_exist)

    if os.path.exists(user_input):
        if should_exist:  # user provides a path to existing file or directory required for RDR
            return user_input
        else:  # RDR may overwrite a file or use a directory already containing files, may need to alert user
            print('Warning: the {} already exists and may be overwritten'.format(fn_or_dir))
            input('Press ↵ Enter to continue...')
            return user_input
    else:
        if should_exist:  # user input error, call ask_path to get an existing path
            os.system('cls')
            print('The {} does not exist'.format(fn_or_dir))
            ask_path(message, fn_or_dir, should_exist)
        else:  # if directory, UI will create it; if filename, UI will record it but do nothing
            if fn_or_dir == 'directory':
                p = Path(user_input)
                p.mkdir(parents=True, exist_ok=True)
            return user_input

def ask_num(message:str = '', dtype:str = 'year', low:Union[int, float] = 1000, high:Union[int, float] = 9999) -> Union[str, float, int]:
    print(message)
    if dtype == 'year':
        prompt = 'Enter a year (format YYYY).\n   >>'
    if dtype == 'int':
        prompt = 'Enter an integer between {} and {}.\n   >>'.format(low, high)
    if dtype == 'float':
        prompt = 'Enter a number between {} and {}.\n   >>'.format(low, high)

    user_input = input(prompt)
    ui.universal_commands(user_input)
    if user_input == '':
        return user_input
    
    try:
        if dtype == 'float':
            user_input = float(user_input)
        else:
            user_input = int(user_input)
    except:
        print('Invalid format.')
        ask_num(message, dtype, low, high)

    if (user_input >= low) and (user_input <= high):
        return user_input
    
    print('{} is not between {} and {}.'.format(user_input, low, high))
    ask_num(message, dtype, low, high)

def ask_string(message:str = '', char_floor:int = 0, char_ceiling:int = 1000, illegal_chars:str = None) -> str:
    print(message)
    user_input = input('Enter text.\n   >>')
    ui.universal_commands(user_input)
    if user_input == '':
        return user_input
    
    no_illegal_chars = set(user_input).isdisjoint(set(illegal_chars))  # borrowed from https://stackoverflow.com/a/17735466

    if len(user_input) >= char_floor:
        if len(user_input) <= char_ceiling:
            if no_illegal_chars:
                return user_input
    
    print('Invalid input.')
    ask_string(message, char_floor, char_ceiling, illegal_chars)

def ask_options(message:str = '', options:list = None) -> Union[str, float, int, bool]:
    print(message)

    n = 1
    for option in options:
        print('\n({}) '.format(n), option)
        n += 1
    
    user_input = input('Enter option (NUMBER).\n   >>')
    ui.universal_commands(user_input)
    if user_input == '':
        return user_input
    
    # TODO: add try-except for conversion to int
    user_input = int(user_input)

    if user_input in list(range(1, n+1)):
        return options[user_input-1]

    os.system('cls')
    print('Invalid input.')
    ask_options(message, options)

def ask_multi(param:Param, message:str = '', info:str = '', mlist:list = None, n:int = 0) -> None:

    for mini_param in mlist:
        mini_param.value = None
    
    if (mlist is None):
        raise Exception('DEV ERROR: List of mini-params must be passed to ask_multi for proper functioning. See another multi in params.py for examples.')

    if (len(mlist) < 1):
        raise Exception('DEV ERROR: List of mini-params must be passed to ask_multi for proper functioning. See another multi in params.py for examples.')
    
    if n == 0:
        print(message)

    if (len(param.mval) < (n+1)) or (len(param.mval) == 0):
        mparam = MultiParam()
        attribute_names = [x.name for x in mlist]
    else:
        mparam = param.mval[n]
        attribute_names = [x for x in list(mparam.attributes().keys())]

        mparam_info = ['\nAttributes for {} item number {} out of {}'.format(param.name, n + 1, len(param.mval))]
        for i, x in mparam.attributes().items():
            mparam_info.append('\n{}: {}'.format(i, x))
    
        print(''.join(mparam_info))

    input_message = '\nType values for {} separated by commas (,)\n   >>'.format(
            ', '.join(
                attribute_names
                ))
    # TODO: reintroduce below functionality using argparse
    # \nOR type "attribute name:: attribute value" pairs with two colons and for multiple pairs, separate with commas.

    # Different input message for multis that have only one mini-param
    if len(mlist) == 1:
        attribute_name = attribute_names[0]
        input_message = '\nType value for {att}. To add another {att}, press Enter key and then type next value.\n   >>'.format(att = attribute_name)

    print('HINT: Type "done" if done setting {}.\nHINT: Type "--NUMBER" (for example: --3) to jump to that item number.'.format(param.name))
    print('HINT: To delete an item, type "deleteNUMBER" (for example delete3) to delete that item number.')
    print('HINT: To delete all items, type deleteALL. (Use this if )')
    
    user_input = input(input_message)
    user_input = user_input.replace("'", '').replace('"', '')
    ui.universal_commands(user_input)

    if user_input.lower() in ['', 'done']:
        sp.main(go_to = 'next')

    elif user_input[0:6] == 'delete':
        uinput = ask_y_n('Are you sure you want to delete item number {}?'.format(user_input[6:]))
        if uinput.lower() == 'y':
            deleted = False
            try:
                
                n = int(user_input[6:]) - 1
                param.mval.pop(n)
                
                deleted = True
            except:
                print('Deletion unsuccessful.')
        
        if deleted:
            n = n - 1
            if n < 0:
                n = 0

        os.system('cls')

        for mini_param in mlist:
            mini_param.value = None

        ask_multi(param, info = info, mlist = mlist, n = n)

    elif user_input == 'deleteALL':
        uinput = ask_y_n('Are you sure you want to delete all items?')
        if uinput.lower() == 'y':
            param.mval.clear()

        os.system('cls')

        for mini_param in mlist:
            mini_param.value = None

        ask_multi(param, info = info, mlist = mlist, n = 0)   

    elif user_input[0:2] == '--':
        try:
            n = int(user_input[2:]) - 1
        except:
            print('Invalid input.')

        os.system('cls')

        for mini_param in mlist:
            mini_param.value = None

        if n < 0:
            n = 0

        ask_multi(param, info = info, mlist = mlist, n = n)

    # TODO: reintroduce below functionality with argparse
    # if '::' in user_input: # TODO: check for :\ in filepaths, strip quotes from filepaths
    #     set_multi_using_attr(param, mparam, info, mlist, user_input, n)

    elif ',' in user_input or len(user_input) > 0:
        set_multi_using_list(param, mparam, info, mlist, user_input, n)

    else:
        uinput = input('Invalid input. Type -h and press Enter key for help, or press Enter key to go back...')
        ui.universal_commands(uinput)

        os.system('cls')
        sp.main(go_to = param.short)

def set_multi_using_list(param:Param, mparam:MultiParam, info:str = '', mlist:list = None, user_input:str = None, n:int = 0) -> None:

    ilist = [x.strip() for x in user_input.split(',')]

    if len(ilist) == len(mlist):

        print('Writing attributes...')

        for mini_param, uinput in zip(mlist, ilist):
            if mini_param.value is None or mini_param.value == '':
                mini_param.value = uinput
                # TODO: add input validation
            if uinput == '':
                continue # Skip blank values

        for mini_param in mlist:
            for attribute_name in list(mparam.__dict__.keys()):
                if attribute_name in mini_param.name:
                    mparam.__dict__[attribute_name] = mini_param.value
        
        if mparam.name[0] is None:  # TODO: figure out why mparam.name is contained in a tuple at this point when name is not assigned
            mparam.name = param.short + '_' + str(n + 1)

        param.mval.append(mparam)

        for mini_param in mlist:
            mini_param.value = None

        ask_multi(param, info = info, mlist = mlist, n = len(param.mval) + 1)

    print('Invalid list of inputs. Expected {} inputs but received {}.'.format(len(mlist), len(ilist)))
    for mini_param in mlist:
        mini_param.value = None
    ask_multi(param, info = info, mlist = mlist, n = n)

def set_multi_using_attr(param, mparam, info = '', mlist = None, user_input = None, n = 0):  # TODO: reintroduce functionality using argparse

    pair_list = [pair.strip(' "') for pair in user_input.split(',')]

    for pair in pair_list:
        pair_split = [item.strip(' "') for item in pair.split('::')]
        for attribute_name in list(mparam.__dict__.keys()):
            if attribute_name in pair_split[0]:
                mparam.__dict__[attribute_name] = pair_split[1]
                # TODO: add input validation

    print('Invalid attribute name-value pair input(s).')
    ask_multi(param, info = info, mlist = mlist, n = n)

def write_bat(python: str, rdr: str, run_bat_file: str, save_file: str) -> None:
    # Adapted with permission from the Freight and Fuel Transportation Optimization Tool https://github.com/VolpeUSDOT/FTOT-Public
    
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(python))), 'Scripts')
    
    with open(run_bat_file, 'w') as wf:
        print("Writing the file: {}".format(run_bat_file))

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
        REM error handling: print message and clean up
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

def quick_save(save_file: Param, param_list: list, go_to: str = 'sequential') -> None:
    if save_file.value is None:
        state_save(params.save_folder, params.save_name, param_list, go_to)
        return

    save_dict = save_params(param_list, go_to)
    with open(save_file.value, 'w', encoding = 'utf-8') as save_state:  # https://stackoverflow.com/a/12309296
        json.dump(save_dict, save_state, ensure_ascii = False)    

def state_save(save_folder: str, save_name: str, param_list: list, go_to: str = 'sequential') -> None:
    save_folder = build_input(save_folder, 'Provide the path for the folder that will contain the RDR UI save file', fn_or_dir = 'directory', should_exist = True)
    save_name = build_input(save_name, "Provide the name of the save file. Do not include the extension, which will be automatically set as '.save'\nThe '.' character is not allowed in the file name", char_floor = 1, char_ceiling = 20, illegal_chars = ['.'])

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

def load_save(save_file: str, param_list: list) -> str:
    user_input = build_input(save_file, 'Provide the path of the RDR UI save file', fn_or_dir = 'filename', should_exist = True)

    user_input = user_input.strip('" ').strip("' ")

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
                parameter.value = save_dict[short]
                break

    return user_input, save_dict['go_to']

def build_input(param: Param, message: str = '', info: str = '', **kwargs) -> Union[str, float, int, bool, None]:
    dtype = param.dtype
    
    if dtype == 'multi':
        if len(param.mval) > 0:
            mnames = [x.name for x in param.mval]
            print('\nParameter name: {}\nNumber of items: {}\nItem name(s)   : {}\nShortcut      : {}'.format(param.name, len(param.mval), mnames, param.short))

            return ask_multi(param, message, info, mlist = kwargs['mlist'])

        print('\nParameter name: {}\nCurrent value: {}\nShortcut      : {}'.format(param.name, param.value, param.short))
        return ask_multi(param, message, info, mlist = kwargs['mlist'])
    
    print('\nParameter name: {}\nCurrent value: {}\nShortcut      : {}'.format(param.name, param.value, param.short))
    if dtype == 'path':
        return ask_path(message, fn_or_dir = kwargs['fn_or_dir'], should_exist = kwargs['should_exist'])

    if dtype in ['year', 'int', 'float']:
        return ask_num(message, dtype, low = kwargs['low'], high = kwargs['high'])

    if dtype == 'str':
        return ask_string(message, char_floor = kwargs['char_floor'], char_ceiling = kwargs['char_ceiling'], illegal_chars = kwargs['illegal_chars'])
    
    if dtype == 'options':
        if param.options is None:
            raise Exception('DEV ERROR: dtype of {} is options. options type params must have a list in its options argument at instantiation.'.format(param.name))
        return ask_options(message, options = param.options)

    raise Exception('DEV ERROR: dtype of {} not set to one of the accepted dtypes. Current dtype is {}. Change dtype or design new interaction for the new dtype.'.format(param.name, param.dtype))

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
            uinput = input('WARNING: {} exists and will be\noverwritten with {}.\nMove it to avoid overwriting.\nPress Enter key to continue...'.format(dest, file))
            ui.universal_commands(uinput)
        try:
            shutil.copy(file, dest)
        except shutil.SameFileError:
            print('WARNING: {} has same source and destination. File not copied.'.format(file))

def move_non_config_files(input_dir: Param, haz: Param, ecf: Param, net: Param, nwn: Param, pri: Param, prt: Param) -> None:
    # TODO: move non-config files to correct locations (or verify locations?)
    # TODO: add base year core model runs file
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
        print('\n\n    The following files associated with the listed parameter could not be located:{}'.format('\n    '.join(error_files)))
        uinput = input('\n\n    Please note these parameters and correct their settings in SET PARAMETERS.\n    Press Enter to be redirected to SET PARAMETERS page...')
        ui.universal_commands(uinput)
        ui.universal_commands('-{}'.format(error_params[0].short))
        
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
