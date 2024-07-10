import argparse
import os
import sys
import pandas as pd

import set_params as sp
import ui_tools as ut
import params
import error_classes as ec

header = "\n\n\
________________________________________________________________________________________\n\n\
       R D R   U I\n\n\n\n\
       UI version 2024.1 alpha\n\n\n\n\
       RDR version 2024.1\n\n\n\n\
       UI created by Kevin Zhang, Andrew Breck, and Juwon Drake at the Volpe Center\n\n\n\n\
________________________________________________________________________________________"

bad_selection = '\n\n\n     Invalid selection.\n\n     Type one of the below options or a universal command and press enter.'

def main():
    os.system('cls')
    print(header)
    
    if params.dev_mode.value:  # Throws warning if RDR UI is in developer mode
        print('\n     WARNING: Launching RDR UI in developer mode.\n     Errors will crash the program without a chance to save and Exception text will not be suppressed.')

    print('\n     WARNING: Do not press Ctrl + C (shortcut for copying to clipboard) as RDR UI will quit without warning and without a chance to save')
    print('\n     At any time, type:\n       -mm for the main menu\n       -h for help\n       -s to save\n       See help menu for list of all commands')
    uinput = input('\n     Press Enter key to continue...')
    universal_commands(uinput)

    os.system('cls')
    main_menu()

def universal_commands(uinput:str) -> None:
    if len(uinput.lower()) > 0:
        if (uinput.lower()[0] == '-') and (uinput.lower()[1] != '-') and not (uinput.lower()[1].isnumeric()):
            uinput = uinput.lower()[1:]
            if uinput.lower() in ['mm', 'main menu']:
                os.system('cls')
                main_menu()

            if uinput.lower() in ['qp', 'exit']:
                os.system('cls')
                close()

            if uinput.lower() == 'qpmz':
                os.system('cls')
                sys.exit()

            if uinput.lower() in ['sa', 'save as']:
                os.system('cls')
                ut.state_save(params.save_folder, params.save_name, params.param_list, go_to = params.current_param.value)
                universal_commands('-cc')

            if uinput.lower() in ['s', 'save', 'savebackto']:
                os.system('cls')
                if uinput.lower() == 'savebackto':
                    ut.quick_save(params.save_file, params.param_list, go_to = params.current_param.value)
                    input('\n\n\n\n   Save successful. Press enter to continue')
                    os.system('cls')
                    build_bat()
                ut.quick_save(params.save_file, params.param_list, go_to = params.current_param.value)
                input('\n\n\n\n   Save successful. Press enter to continue')
                universal_commands('-cc')

            if uinput.lower() in ['l', 'load']:
                os.system('cls')
                load_save()

            if uinput.lower() in ['cc', 'current']:
                os.system('cls')
                sp.main(params.current_param.value)

            if uinput.lower() in ['bb', 'back']:
                os.system('cls')
                sp.main(params.previous_param.value)

            if uinput.lower() in ['h', 'help']:
                os.system('cls')
                help_page()

            if uinput.lower() in ['cb', 'batch']:
                os.system('cls')
                build_bat()

            if uinput.lower() in params.shorts:
                os.system('cls')
                sp.main(uinput.lower())

            if uinput.lower() in params.shortbackto:  # Forces RDR UI back to a non-Set Parameters page
                os.system('cls')
                sp.main(uinput.lower())

            print('       \n\n\n\nInvalid command. Type -h for help.')

def main_menu() -> None:
    print('\n\n\n\n   MAIN MENU\n\n   (1) Load Save File\n\n   (2) Set RDR Parameters\n\n   (3) Help\n\n   (4) View Current Values for Parameters\n\n   (9) Create RDR batch file\n\n   (0) Close')

    uinput = input('\n\n   Select a (NUMBER) and press Enter\n   >>')
    universal_commands(uinput)

    if uinput == '1':
        os.system('cls')
        load_save()
    elif uinput == '2':
        os.system('cls')
        sp.main(params.current_param.value)
    elif uinput == '3':
        os.system('cls')
        help_page()
    elif uinput == '4':
        os.system('cls')
        param_summary()
    elif uinput == '9':
        os.system('cls')
        build_bat()
    elif uinput == '0':
        os.system('cls')
        close()
    else:  # else statements should catch non-valid options and use recursion to take user back to an input phase
        os.system('cls')
        print(bad_selection)
        main_menu()
        
def load_save() -> None:
    os.system('cls')
    print("\n\n\n\n      LOAD SAVE")
    sp.main(load_save = True)

def param_summary() -> None:
    os.system('cls')
    param_shorts_summary = pd.DataFrame.from_dict(params.short_dict, orient='index', columns=['Shortcut'])
    save_dict = ut.save_params(param_list = params.param_list, go_to = params.current_param.value)
    param_curr_values = pd.DataFrame.from_dict(save_dict, orient='index', columns=['Current Value'])
    param_summary = pd.merge(param_shorts_summary, param_curr_values, how='left', left_on='Shortcut', right_index=True)
    param_summary['Shortcut'] = '-' + param_summary['Shortcut']
    param_summary = param_summary.explode('Current Value')
    param_summary['Current Value'] = param_summary['Current Value'].astype(str).str.slice(0,38)
    #csv_filepath = r"C:\GitHub\RDR\Data\UI_files\param_summary.csv"
    #param_summary.to_csv(csv_filepath)
    print('\n\n\n\nPARAMETERS, SHORTCUT COMMANDS TO ACCESS THEM, AND THEIR CURRENT VALUES\n\nTo search for a parameter on this page, press "Ctrl" and "f"\nType "-mm" for main menu or "-h" for main help page, followed by Enter\n\n')
    with pd.option_context('display.max_rows', None,
                    'display.max_columns', None,
                    'display.html.border', 5,
                    ):
        print(param_summary)
    uinput = input('\n\nTo search for a parameter on this page, press "Ctrl" and "f"\nType "-mm" for main menu or "-h" for main help page, followed by Enter\n>>')
    universal_commands(uinput)

def help_page() -> None:
    
    universal_command_summary = pd.DataFrame([['Return to main menu',['-mm', '-main menu']],
                                              ['Quit program',['-qp', '-exit']],
                                              ['Save as',['-sa', '-save as']],
                                              ['Save',['-s', '-save']],
                                              ['Load save',['-l', '-load']],
                                              ['Create RDR batch file',['-cb', '-batch']],
                                              ['Return to most recently visited parameter page',['-cc', '-current']],
                                              ['Return to most recently completed parameter page',['-bb', '-back']],
                                              ['Return to main help page',['-h', '-help']]], 
                                             columns = [' ','Universal Command Options']
                                             ).set_index(' ')

    print('\n\n\n\n   HELP PAGE\n\n   To return to the main menu, type "-mm" or "-main menu" and press Enter.\n   To return to the parameter entry page you were most recently viewing, type "-cc" or "-current" and press Enter.\n   To return to the prior parameter entry page, type "-bb" or "-back" and press Enter.\n\n   Help Menu Options:\n\n   (1) View Universal Commands\n\n   (2) View Parameters, Shortcut Commands to Access Them, and Their Current Values')
    uinput = input('\n\n   Select a (NUMBER) and press Enter\n   >>')
    universal_commands(uinput)
    if uinput == '1':
        os.system('cls')
        print('\n\n\n\nUNIVERSAL COMMANDS\n\nUse these commands at any time, followed by Enter, for each specified action.\n\n')
        with pd.option_context('display.max_rows', None,
                       'display.max_columns', None,
                       'display.html.border', 5,
                       ):
            print(universal_command_summary)
        uinput = input('\nTo return to the main help page, type "-h" and press Enter, or choose one of the other universal commands above.\n>>')
        universal_commands(uinput)
    elif uinput == '2':
        param_summary()
    os.system('cls')
    main_menu()

def build_bat() -> None:
    # Adapted with permission from the Freight and Fuel Transportation Optimization Tool https://github.com/VolpeUSDOT/FTOT-Public
    print("\n\n\n\n      CREATE RDR BATCH FILE")

    # Batch file location
    print("\n\n      Current batch folder location: {}".format(params.bat_location.value))
    if params.bat_location.value is None:
        input('\n\n\n        Batch file location not set. Redirecting to Set Parameters. Press Enter...')
        pushinput = ''.join(['-', params.bat_location.short, 'backto'])
        universal_commands(pushinput)

    # Python environment
    print("\n\n      Current python.exe path: {}\n      Shortcut: -{}".format(params.python.value, params.python.short))
    if params.python.value is None:
        input('\n\n\n        python.exe file path not set. Redirecting to Set Parameters. Press Enter...')
        pushinput = ''.join(['-', params.python.short, 'backto'])
        universal_commands(pushinput)

    # RDR program directory
    print("\n\n      Current Run_RDR.py path: {}\n      Shortcut: -{}".format(params.rdr.value, params.rdr.short))
    if params.rdr.value is None:
        input('\n\n\n        Run_RDR.py file path not set. Redirecting to Set Parameters. Press Enter...')
        pushinput = ''.join(['-', params.rdr.short, 'backto'])
        universal_commands(pushinput)

    # Run ID
    print("\n\n      Current run ID (will be used to name the batch file): {}\n      Shortcut: -{}".format(params.run_id.value, params.run_id.short))
    if params.run_id.value is None:
        input('\n\n\n        Run ID not set. Redirecting to Set Parameters. Press Enter...')
        pushinput = ''.join(['-', params.run_id.short, 'backto'])
        universal_commands(pushinput)

    # Input dir
    print("\n\n      Current input directory: {}\n      Shortcut: -{}".format(params.input_dir.value, params.input_dir.short))
    if params.input_dir.value is None:
        input('\n\n\n        Input directory not set. Redirecting to Set Parameters. Press Enter...')
        pushinput = ''.join(['-', params.input_dir.short, 'backto'])
        universal_commands(pushinput)

    # Save file
    print("\n\n      Current save file: {}\n      Shortcut: -{}".format(params.save_file.value, 'save'))
    if params.save_file.value is None:
        input('\n\n\n        No save file detected. RDR UI will now save. Press Enter...')
        pushinput = ''.join(['-', 'save', 'backto'])
        universal_commands(pushinput)

    uinput = input('\n\n      To modify a parameter, type its shortcut and press enter to specify.\n      To continue without modifications, press enter.\n>>')
    if uinput == '':
        os.system('cls')
        # Move non-config files to correct locations
        print('\n      Current input directory: {}'.format(params.input_dir.value))
        uinput = input('\n      To continue, press Enter.  \n>>')
        if uinput == '':
            os.system('cls')
            ut.move_non_config_files(input_dir = params.input_dir.value, 
                                     haz = params.hazards, 
                                     ecf = params.economic_futures, 
                                     net = params.network_links, 
                                     nwn = params.net_node, 
                                     pri = params.proj_info, 
                                     prt = params.proj_table)
            print('\n\n      Hazards, AEMaster, Networks, and LookupTables directories successfully created and associated files copied. Starting batch file creation...')
            # Creat the batch file
            run_bat_file = ut.create_bat(python = params.python.value, rdr = params.rdr.value, bat_location = params.bat_location.value, run_id = params.run_id.value, save_file = params.save_file.value)

            input("\n\n\n\n      Batch file saved to: {}\n\n Press enter to return to main menu.".format(run_bat_file))

            os.system('cls')
            main_menu()

    if uinput.lower in [''.join(['-', params.run_id.short]), ''.join(['-', params.rdr.short]), ''.join(['-', params.python.short]), ''.join(['-', params.bat_location.short]), '-save']:
        uinput = ''.join([uinput, 'backto'])
    universal_commands(uinput)

    print(bad_selection)
    os.system('cls')
    build_bat()

def close() -> None:
    print("\n\n\n\n      CLOSE RDR UI")
    uinput = ut.ask_y_n('\n\n\n\n   Unsaved progress will be lost.\n\n\n\n   Continue?\n   ')
    universal_commands(uinput)

    if uinput.lower() == 'y':
        os.system('cls')
        sys.exit()
    elif uinput.lower() == 'n':
        os.system('cls')
        main_menu()
    else:
        print(bad_selection)
        close()

if params.dev_mode.value:  # Universal error catching disabled if dev_mode.value is True, Exception text is not suppressed
    if __name__ == "__main__":
        main()

else:  # Universal error catching enabled, Exception text is suppressed and user can save
    try:
        if __name__ == "__main__":
            main()
    except Exception as e:
        os.system('cls')
        if e.__class__.__name__ == "JSONDecodeError":
            msg = ec.JSON_load_save_error()
            print(msg)
        else:
            print(e)
        input('An error occurred as described above.\nPress Enter to verify save file location before the program exits...')
        ut.state_save(params.save_folder, params.save_name, params.param_list, go_to = params.current_param.value)
        sys.exit()
