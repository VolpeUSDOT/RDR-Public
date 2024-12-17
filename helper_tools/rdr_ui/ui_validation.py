# Helper tools for RDR UI
import os
from typing import Union

from params import Param

def validate_path(fn_or_dir: str = 'unspecified', user_input: str = '') -> str:
    # TODO: add quote stripping
    # the path should be a filename if that is specified in fn_or_dir of the param, same for directory
    # this only checks if the path actually exists
    errors = []
    if os.path.isdir(user_input) and fn_or_dir == 'directory':
        return errors
    if os.path.isfile(user_input) and fn_or_dir == 'filename':
        return errors
    if os.path.exists(user_input) and fn_or_dir == 'unspecified':
        return errors

    if os.path.isdir(user_input) and fn_or_dir == 'directory':
        errors.append("ERROR: Invalid entry. Enter a file path instead of a directory (folder) path.")
    elif os.path.isfile(user_input) and fn_or_dir == 'filename':
        errors.append("ERROR: Invalid entry. Enter a directory (folder) path instead of a file path.")
    elif not os.path.exists(user_input) and fn_or_dir == 'unspecified':
        errors.append("ERROR: Invalid entry. Could not locate {}.".format(user_input))
    else:
        errors.append("ERROR: Invalid entry. The path to the {} is not recognized.".format(fn_or_dir))
    
    return errors

def validate_num(dtype:str = 'year', low:Union[int, float] = -9999999, high:Union[int, float] = 9999999, user_input: str = '')-> Union[str, float, int]:
    
    errors = []

    if dtype == 'float':
        try:
            user_input = float(user_input)
            if (user_input < low) or (user_input > high):
                errors.append('ERROR: Input must be between {} and {}, inclusive.'.format(low, high))
        except:
            errors.append('ERROR: Input is not a number.')
    else:
        try:
            user_input = int(user_input)
            if (user_input < low) or (user_input > high):
                errors.append('ERROR: Input must be between {} and {}, inclusive.'.format(low, high))
        except:
            errors.append('ERROR: Input must be an integer.')
    
    return errors

def validate_string(char_floor:int = 0, char_ceiling:int = 1000, illegal_chars:str = ',', user_input: str = '') -> str:
    
    no_illegal_chars = set(user_input).isdisjoint(set(illegal_chars))  # borrowed from https://stackoverflow.com/a/17735466
    errors = []

    if len(user_input) <= char_floor:
        errors.append('ERROR: Input contains less than the minimum number of characters, which is {}.'.format(char_floor))
    if len(user_input) >= char_ceiling:
        errors.append('ERROR: Input contains more than the maximum number of characters, which is {}.'.format(char_ceiling))
    if not no_illegal_chars:
        flagged_chars = set(illegal_chars).intersection(set(user_input))
        errors.append('ERROR: Input contains the character(s) "{}", which is(are) not allowed in this input.'.format(flagged_chars))
            
    return errors

def validate_options(user_input: str = '', n: int = 0) -> bool:
    
    errors = []
    # TODO: add try-except for conversion to int
    try:
        user_input = int(user_input)
    except:
        errors.append('ERROR: Input is not an integer.')
        return errors # Need to immediately return because the next test will throw an Exception

    if not (user_input in list(range(1, n+1))):
        errors.append('ERROR: Input is outside of range of options.')
        
    return errors


def validate_mini(param: Param, user_input: str = '') -> bool:
    dtype = param.dtype
    
    if dtype == 'path':
        return validate_path(user_input = user_input)

    if dtype in ['year', 'int', 'float']:
        return validate_num(user_input = user_input, dtype = dtype)

    if dtype == 'str':
        return validate_string(user_input = user_input)
    
    # Options is not used in multis
    # if dtype == 'options':
    #     return validate_options(user_input = user_input, options = param.options, n = kwargs['n'])

    raise Exception('DEV ERROR: dtype of {} not set to one of the accepted dtypes for non-config validation. Current dtype is {}. Change dtype or design new interaction for the new dtype.'.format(param.name, param.dtype))
