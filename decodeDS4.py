"""
Functions to get inputs from a DualShock 4 controller HID device
Referenced from https://www.psdevwiki.com/ps4/DS4-USB#Report_Structure

hidReport is the list of numbers (0 to 255) returned by reading the HID device
"""

def get_xLeftStick(hidReport):
    """Get left stick x position (-1-1), 0 is left"""
    return 2 * hidReport[1] / 255 - 1

def get_yLeftStick(hidReport):
    """Get left stick y position (0-1), 0 is up"""
    return 2 * hidReport[2] / 255 - 1

def get_xRightStick(hidReport):
    """Get left stick x position (-1-1), 0 is left"""
    return 2 * hidReport[3] / 255 - 1

def get_yRightStick(hidReport):
    """Get left stick y position (-1-1), 0 is up"""
    return 2 * hidReport[4] / 255 - 1

def get_buttonTri(hidReport):
    """Get triangle button (0 or 1), 1 is pressed"""
    return int(f"{hidReport[5]:08b}"[0])

def get_buttonCirc(hidReport):
    """Get circle button (0 or 1), 1 is pressed"""
    return int(f"{hidReport[5]:08b}"[1])

def get_buttonX(hidReport):
    """Get X button (0 or 1), 1 is pressed"""
    return int(f"{hidReport[5]:08b}"[2])

def get_buttonSquare(hidReport):
    """Get square button (0 or 1), 1 is pressed"""
    return int(f"{hidReport[5]:08b}"[3])

def get_directionDPad(hidReport):
    """Get D-Pad input direction (N, NE, E, SE, S, SW, W, NW, and - for unpressed)"""
    match f"{hidReport[5]:08b}"[4:]:
        case "0000":
            return "N"
        case "0001":
            return "NE"
        case "0010":
            return "E"
        case "0011":
            return "SE"
        case "0100":
            return "S"
        case "0101":
            return "SW"
        case "0110":
            return "W"
        case "0111":
            return "NW"
        case "1000":
            return "-"
    return None

def get_buttonRightStick(hidReport):
    """Get right stick press (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[0])

def get_buttonLeftStick(hidReport):
    """Get left stick press (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[1])

def get_buttonOption(hidReport):
    """Get option button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[2])

def get_buttonShare(hidReport):
    """Get share button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[3])

def get_buttonR2(hidReport):
    """Get R2 button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[4])

def get_buttonL2(hidReport):
    """Get L2 button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[5])

def get_buttonR1(hidReport):
    """Get R1 button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[6])

def get_buttonL1(hidReport):
    """Get L1 button (0 or 1), 1 for pressed"""
    return int(f"{hidReport[6]:08b}"[7])

def get_buttonTPad(hidReport):
    """Get T-Pad click (0 or 1), 1 for pressed"""
    return int(f"{hidReport[7]:08b}"[6])

def get_buttonPS(hidReport):
    """Get PS button(0 or 1), 1 for pressed"""
    return int(f"{hidReport[7]:08b}"[7])

def get_triggerL2(hidReport):
    """Get L2 trigger position (0-1), 0 is off"""
    return hidReport[8] / 255

def get_triggerR2(hidReport):
    """Get R2 trigger position (0-1), 0 is off"""
    return hidReport[9] / 255
