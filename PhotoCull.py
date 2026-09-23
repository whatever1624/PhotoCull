import os
import hid
import time
import tkinter
import decodeDS4
from PIL import ExifTags, Image, ImageOps, ImageTk

### File and Folder Settings ###
startPhotoName: str = ".JPG"
photoFolder: str = '/Users/willow/Pictures/Olympus E-M1 III/0 - Backup for SD Card Culling'
photoFileExts: list[str] = ['.jpg', '.png', '.orf', '.raf']
deleteFolderName: str = "PHOTOCULL DELETE"
# TODO: Sort options (name, EXIF time)

### Control Settings ###
ds4VendorID: int = 0x054c
ds4ProductID: int = 0x09cc
rZoomMax: float = 2
zoomSpeed: float = 1
panSpeed: float = 2000
rDeadzone: float = 0.05

### GUI Settings ###
maxWindowSize: list[int] = [10000, 10000]  # Set arbitrarily large for max size
infoFontSize: int = 11
textColour: str = "#FFF"
backgroundColour: str = "#000"
BShareTextBuffers = False

### Performance Settings ###
fpsLimit: float = 30
rDownsample: int = 2        # Factor to downsample the image to improve performance (1 for no downsampling)
BFastResample: bool = False  # Whether to use fast but lower quality (HAMMING) resampling over max quality (LANCZOS)

def wrap(x, lowerBound, upperBound):
    """Wraps value between the lower (inclusive) and upper (exclusive) bounds"""
    return lowerBound + ((x - lowerBound) % (upperBound - lowerBound))

def clamp(x, lowerBound, upperBound):
    """Clamps value to be between the lower and upper bounds, or to average of the bounds if they are out of order"""
    return max(lowerBound, min(x, upperBound)) if lowerBound < upperBound else (lowerBound + upperBound) / 2

# Toggle control variables
BRememberZoom = False
BRememberPan = False
BShowingDeleteText = False
BShowDeleted = False

# Toggle control button pressed variables
BPressedZoom = False
BPressedPan = False
BPressedDelete = False
BPressedShowDeleted = False

# List HID devices as vendor_id:product_id | product_string
print("HID devices:")
hidDevices = {f"0x{d['vendor_id']:04x}:0x{d['product_id']:04x}": d['product_string'] for d in hid.enumerate()}
hidDevices = dict(sorted(hidDevices.items()))
print("\n".join([f"\t{key} | {val}" for key, val in hidDevices.items()]))

# Connect to DualShock 4 controller
print(f"Connecting to DualShock 4 controller at {ds4VendorID:04x}:{ds4ProductID:04x}")
lenReport = 8 * 64
ds4 = hid.device()
try:
    ds4.open(ds4VendorID, ds4ProductID)
    ds4.set_nonblocking(True)
except OSError:
    print("Failed to connect")

# Create the delete folder
deleteFolder = os.path.join(photoFolder, deleteFolderName)
print(f"Creating delete folder {deleteFolder}")
try:
    os.mkdir(deleteFolder)
except FileExistsError:
    print(f"Delete folder already exists")

# Get all photos in the folder matching the valid file extensions, in ascending path order
print(f"Finding photos with extensions {photoFileExts} in folder {photoFolder}")
photoPaths = [entry.path for entry in list(os.scandir(photoFolder)) + list(os.scandir(deleteFolder))
              if entry.is_file() and any([entry.name.lower().endswith(ext.lower()) for ext in photoFileExts])]
photoPaths.sort(key=lambda p: os.path.split(p)[1])
nPhotos = len(photoPaths)
print(f"Found {nPhotos} photos " +
      f"({len([path for path in photoPaths if path.startswith(deleteFolder)])} in delete folder)")
if nPhotos == 0:
    exit()

# Find the index of the start photo
print(f"Finding index of the start photo {startPhotoName}")
try:
    index = [os.path.split(path)[1].lower() for path in photoPaths].index(startPhotoName.lower())
    if photoPaths[index].startswith(deleteFolder):
        BShowDeleted = True
    print(f"Start photo index: {index}{' (Deleted)' if BShowDeleted else ''}")
except ValueError:
    index = 0
    print(f"Start photo not found, starting from index 0 as fallback")

# Set up the GUI
print("Starting GUI")
sidePanelWidth = 0
window = tkinter.Tk()
window.title("PhotoCull")
window.geometry(f"{int(maxWindowSize[0])}x{int(maxWindowSize[1])}+0+0")
window.configure(background=backgroundColour)
window.update()

# TODO: Set window icon (https://stackoverflow.com/questions/52826692/set-tkinter-icon-on-mac-os)

# GUI loop
BUpdateFull = False
prevIndex = -1
prevWindowGeometry = [0, 0, 0, 0]
dtmsTarget = 1e3 / fpsLimit
dtnsTarget = 1e9 / fpsLimit
dtns = dtnsTarget
tns = time.time_ns()
tnsNext = tns + dtnsTarget
while True:
    # Update window title with framerate
    window.title(f"PhotoCull (FPS: {1e9 / dtns:.1f})")

    # Get window geometry
    windowGeometry = [int(geo) for geo in window.geometry().replace('x', '+').split('+')]
    windowWidth, windowHeight, windowOffsetH, windowOffsetV = windowGeometry
    photoWindowWidth = windowWidth - sidePanelWidth
    if windowGeometry[:2] != prevWindowGeometry[:2]:
        BUpdateFull = True
    prevWindowGeometry = windowGeometry

    # New photo (also true if first loop iteration)
    if index != prevIndex:
        BUpdateFull = True
        tmsLoadStart = time.time() * 1e3
        # Update photo path
        prevIndex = index
        # Open photo (storing the original, but reduced if rDownsample is not 1)
        photoOriginal = ImageOps.exif_transpose(Image.open(photoPaths[index]))
        if rDownsample != 1:
            photoOriginal = photoOriginal.reduce(rDownsample)
        photoOriginalWidth = photoOriginal.width
        photoOriginalHeight = photoOriginal.height
        photoOriginalAspectRatio = photoOriginalWidth / photoOriginalHeight
        # Resize and focus targets
        rResizeTarget = rResize if BRememberZoom else 0
        xFocusTarget = xFocus if BRememberPan else photoOriginalWidth / 2
        yFocusTarget = yFocus if BRememberPan else photoOriginalHeight / 2
        # Resize and focus values
        rResize = 1
        xFocus = -1
        yFocus = -1
        # Read Exif data and strip leading and trailing whitespace
        exif = dict(photoOriginal.getexif()) | photoOriginal.getexif().get_ifd(0x8769)
        photoExif = {ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS}
        for key, val in photoExif.items():
            if isinstance(val, str):
                photoExif[key] = val.strip()
        # Info text
        infoTextDict = {f'Photo ({index + 1}/{nPhotos})': f"{os.path.split(photoPaths[index])[1]} " +
                                                          f"(loaded in {time.time() * 1e3 - tmsLoadStart:.0f} ms)",
                        ' ': "",
                        'Date': photoExif['DateTimeOriginal'].split(' ')[0].replace(':', '-'),
                        'Time': photoExif['DateTimeOriginal'].split(' ')[1],
                        '  ': "",
                        'Camera': f"{photoExif['Make']} {photoExif['Model']}",
                        'Lens': photoExif['LensModel'],
                        'Dimensions': f"{photoOriginalWidth} x {photoOriginalHeight} " +
                                      f"({photoOriginalWidth * photoOriginalHeight * 1e-6:.3} MP)",
                        '   ': f"Downsampled by {rDownsample}x\n" if rDownsample != 1 else "",
                        'Exposure': f"{'+' if photoExif['ExposureBiasValue'] >= 0 else ''}" +
                                                 f"{photoExif['ExposureBiasValue']}",
                        '    ': "",
                        'ISO': f"{photoExif['ISOSpeedRatings']}",
                        'Aperture': f"f/{photoExif['FNumber']}",
                        'Shutter Speed': f"{photoExif['ExposureTime']}\"" if photoExif['ExposureTime'] >= 1
                                         else f"1/{1 / photoExif['ExposureTime']}",
                        '     ': "",
                        'Focal Length': f"{float(photoExif['FocalLength']):.0f} mm"}
        # Controls text
        controlsTextDict = {'Next Photo': "▶",
                            'Previous Photo': "◀",
                            'Jump Zoom In': "▲",
                            'Jump Zoom Out': "▼",
                            'Zoom In': "R2",
                            'Zoom Out': "L2",
                            'Pan': "Left Joystick",
                            'Toggle Remember Zoom': "R1",
                            'Toggle Remember Pan': "L1",
                            'Toggle Move to Delete': "x",
                            'Toggle Show Deleted': "△",
                            ' ': "",
                            'Quit': "T-Pad Click"}

    # Build toggle text and check if mismatched from previously displayed toggle text
    prevToggleTextDict = {} if BUpdateFull else toggleTextDict
    toggleTextDict = {'REMEMBER ZOOM' if BRememberZoom else 'Remember Zoom': "ON" if BRememberZoom else "Off",
                      'REMEMBER PAN' if BRememberPan else 'Remember Pan': "ON" if BRememberPan else "Off",
                      ' ': "",
                      'SHOW DELETED PHOTOS' if BShowDeleted else 'Show Deleted Photos': "ON" if BShowDeleted else "Off"}
    if toggleTextDict != prevToggleTextDict:
        BUpdateFull = True

    # Mismatched photo resize ratio with photo resize target (also true if new photo)
    if BUpdateFull or rResize != rResizeTarget:
        # Apply resize ratio bounds (where the lower bound still fills the window)
        rResizeTarget = clamp(rResizeTarget,
                              min(photoWindowWidth / photoOriginalWidth, windowHeight / photoOriginalHeight),
                              rZoomMax * rDownsample)
        # Resize photo
        if rResize != rResizeTarget:
            BUpdateFull = True
            rResize = rResizeTarget
            resize = (int(photoOriginalWidth * rResize), int(photoOriginalHeight * rResize))
            resample = Image.Resampling.HAMMING if BFastResample else Image.Resampling.LANCZOS
            reducing_gap = 1.0 if BFastResample else None
            tkPhoto = ImageTk.PhotoImage(photoOriginal.resize(resize, resample=resample, reducing_gap=reducing_gap))
            photoWidth = tkPhoto.width()
            photoHeight = tkPhoto.height()

    # Mismatched focus coordinates (also true if new photo or zoom changed)
    if BUpdateFull or xFocus != xFocusTarget or yFocus != yFocusTarget:
        # Apply focus bounds (to ensure the image cannot pan away)
        xFocusTarget = clamp(xFocusTarget,
                             photoWindowWidth / 2 / rResize,
                             photoOriginalWidth - (photoWindowWidth / 2 / rResize))
        yFocusTarget = clamp(yFocusTarget,
                             windowHeight / 2 / rResize,
                             photoOriginalHeight - (windowHeight / 2 / rResize))
        # Calculate photo widget placement
        if BUpdateFull or xFocus != xFocusTarget or yFocus != yFocusTarget:
            BUpdateFull = True
            xPhotoWidget = (photoWindowWidth - photoWidth) / 2 + (photoOriginalWidth / 2 - xFocusTarget) * rResize
            yPhotoWidget = (windowHeight - photoHeight) / 2 + (photoOriginalHeight / 2 - yFocusTarget) * rResize
            xFocus = xFocusTarget
            yFocus = yFocusTarget

    # Full GUI update
    if BUpdateFull:
        BUpdateFull = False
        # Close widgets
        try:
            photoWidget.destroy()
            textWidget.destroy()
        except NameError:
            # First loop iteration
            BUpdateFull = True
            rResizeTarget = 0
        # Generate text
        text = ""
        maxBuffer = max([len(key) for key in infoTextDict.keys() | controlsTextDict.keys()]) + 1
        buffer = maxBuffer if BShareTextBuffers else max([len(key) for key in infoTextDict.keys()]) + 1
        for key, val in infoTextDict.items():
            text += f"{key}{' ' if key.replace(' ', '') == "" else ':'}{' ' * (buffer - len(key))}{val}\n"
        text += "\n\n" + '—' * max([len(line) for line in text.split('\n')]) + "\n\n\n"
        buffer = maxBuffer if BShareTextBuffers else max([len(key) for key in controlsTextDict.keys()]) + 1
        for key, val in controlsTextDict.items():
            text += f"{key}{' ' if key.replace(' ', '') == "" else ':'}{' ' * (buffer - len(key))}{val}\n"
        text += "\n\n" + '—' * max([len(line) for line in text.split('\n')]) + "\n\n\n"

        buffer = maxBuffer if BShareTextBuffers else max([len(key) for key in toggleTextDict.keys()]) + 1
        for key, val in toggleTextDict.items():
            text += f"{key}{' ' if key.replace(' ', '') == "" else ':'}{' ' * (buffer - len(key))}{val}\n"

        # Photo widget and delete text
        photoWidget = tkinter.Canvas(window, bg=backgroundColour, highlightthickness=0)
        photoWidget.create_image(xPhotoWidget + photoWidth / 2, yPhotoWidget + photoHeight / 2, image=tkPhoto)
        if photoPaths[index].startswith(deleteFolder):
            BShowingDeleteText = True
            t = photoWidget.create_text(photoWindowWidth / 2, windowHeight / 2, text="⌫", fill=textColour)
            # Binary search to resize the font to fill the photo window width
            lbFontSize = 1
            ubFontSize = 0
            while ubFontSize - lbFontSize != 1:
                fontSize = lbFontSize * 2 if lbFontSize > ubFontSize else (ubFontSize + lbFontSize) // 2
                photoWidget.itemconfigure(t, font=('PT Sans', fontSize, 'bold'))
                if min(photoWidget.bbox(t)) > 0:
                    lbFontSize = fontSize
                else:
                    ubFontSize = fontSize
        else:
            BShowingDeleteText = False
        if not BUpdateFull:
            # Don't place the photo widget if it is the first loop iteration
            photoWidget.place(width=photoWindowWidth, height=windowHeight)

        # Info text widget (After the photo widget to be the top layer)
        textWidget = tkinter.Label(window, text=text, font=('PT Mono', infoFontSize), justify='left',
                                   fg=textColour, bg=backgroundColour, anchor='n')
        charWidth = textWidget.winfo_reqwidth() / max([len(line) for line in text.split('\n')])
        textWidget.configure(padx=2 * charWidth, pady=2 * charWidth)
        sidePanelWidth = textWidget.winfo_reqwidth()
        textWidget.place(x=windowWidth - sidePanelWidth, y=0, width=sidePanelWidth, height=windowHeight)

    # Update window
    window.update()

    # Controller input
    try:
        ds4Report = ds4.read(lenReport, dtmsTarget)
        directionDPad = decodeDS4.get_directionDPad(ds4Report)
        # Next/Previous photo - D-Pad right (E) / D-Pad left (W)
        if directionDPad in ['E', 'W']:
            for i in range(nPhotos):
                index = wrap(index + (1 if directionDPad == 'E' else -1), 0, nPhotos)
                if BShowDeleted or not photoPaths[index].startswith(deleteFolder):
                    break
            else:
                print("0 undeleted photos")
                exit()
        # Zoom - R2 trigger (in) and L2 trigger (out)
        triggerR2 = max(0, decodeDS4.get_triggerR2(ds4Report) - rDeadzone) / (1 - rDeadzone)
        triggerL2 = max(0, decodeDS4.get_triggerL2(ds4Report) - rDeadzone) / (1 - rDeadzone)
        rResizeTarget *= 1 + 1e-9 * dtns * zoomSpeed * (triggerR2 - triggerL2)
        # Jump zoom in - D-Pad up (N)
        if directionDPad == 'N':
            rResizeTarget = rZoomMax * rDownsample
        # Jump zoom out - D-Pad down (S)
        if directionDPad == 'S':
            rResizeTarget = 0
        # Pan - Left joystick position
        xLeftStick = decodeDS4.get_xLeftStick(ds4Report)
        xLeftStick = max(0, (abs(xLeftStick) - rDeadzone)) / (1 - rDeadzone) * (1 if xLeftStick > 0 else -1)
        yLeftStick = decodeDS4.get_yLeftStick(ds4Report)
        yLeftStick = max(0, (abs(yLeftStick) - rDeadzone)) / (1 - rDeadzone) * (1 if yLeftStick > 0 else -1)
        xFocusTarget += 1e-9 * dtns * panSpeed / rResize * xLeftStick
        yFocusTarget += 1e-9 * dtns * panSpeed / rResize * yLeftStick
        # Remember zoom ratio - R1 button
        if decodeDS4.get_buttonR1(ds4Report):
            if not BPressedZoom:
                BRememberZoom = not BRememberZoom
            BPressedZoom = True
        else:
            BPressedZoom = False
        # Remember pan location - L1 button
        if decodeDS4.get_buttonL1(ds4Report):
            if not BPressedPan:
                BRememberPan = not BRememberPan
            BPressedPan = True
        else:
            BPressedPan = False
        # Toggle move to delete folder - X button
        if decodeDS4.get_buttonX(ds4Report):
            if not BPressedDelete:
                BUpdateFull = True
                # Move the photo to/from the delete folder and update photo paths index
                if photoPaths[index].startswith(deleteFolder):
                    newPath = os.path.join(photoFolder, os.path.split(photoPaths[index])[1])
                    os.rename(photoPaths[index], newPath)
                    photoPaths[index] = newPath
                else:
                    newPath = os.path.join(deleteFolder, os.path.split(photoPaths[index])[1])
                    os.rename(photoPaths[index], newPath)
                    photoPaths[index] = newPath
                    # Go to next photo
                    if not BShowDeleted:
                        for i in range(nPhotos):
                            index = wrap(index + 1, 0, nPhotos)
                            if not photoPaths[index].startswith(deleteFolder):
                                break
                        else:
                            print("0 undeleted photos")
                            exit()
            BPressedDelete = True
        else:
            BPressedDelete = False
        # Toggle show deleted photos - Triangle button
        if decodeDS4.get_buttonTri(ds4Report):
            if not BPressedShowDeleted:
                BShowDeleted = not BShowDeleted
                if photoPaths[index].startswith(deleteFolder) and not BShowDeleted:
                    for i in range(nPhotos):
                        index = wrap(index + 1, 0, nPhotos)
                        if not photoPaths[index].startswith(deleteFolder):
                            break
                    else:
                        print("0 undeleted photos")
                        exit()

            BPressedShowDeleted = True
        else:
            BPressedShowDeleted = False

        # TODO:
        #   Rotate CCW and save (Square button)
        #   Rotate CW and save (Circle button)

        # Quit - T-Pad button
        if decodeDS4.get_buttonTPad(ds4Report):
            print("Quitting GUI")
            exit()

    except ValueError:
        pass

    # FPS limit
    tns = time.time_ns()
    if tns >= tnsNext:
        dtns = tns - tnsNext + dtnsTarget
        tnsNext = tns + dtnsTarget
    else:
        dtns = dtnsTarget
        while time.time_ns() < tnsNext:
            time.sleep(1e-3)
        tns = tnsNext
        tnsNext += dtnsTarget
