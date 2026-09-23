"""
Move RAW photos to a subfolder if they don't have a matching reference photo
"""
import os

### File and Folder Settings ###
refPhotoFolder: str = '/Users/willow/Pictures/Olympus E-M1 III/0 - Backup for SD Card Culling'
rawPhotoFolder: str = '/Users/willow/Pictures/Olympus E-M1 III/0 - Backup for SD Card Culling/RAW (All)'
refFileExt = '.jpg'
rawFileExt = '.orf'
deleteFolderName: str = "RAW DELETE"

# Create the delete folder
deleteFolder = os.path.join(rawPhotoFolder, deleteFolderName)
print(f"Creating delete folder {deleteFolder}")
try:
    os.mkdir(deleteFolder)
except FileExistsError:
    print(f"Delete folder already exists")

# Get reference photos
refFileExt = refFileExt.lower()
refNames = []
for entry in os.scandir(refPhotoFolder):
    refName = entry.name.lower()
    if refName.endswith(refFileExt):
        refNames.append(refName.replace(refFileExt, ''))
refNames.sort()
print(f"Found {len(refNames)} reference photos in {refPhotoFolder}")

# Get raw photos to delete
rawFileExt = rawFileExt.lower()
deleteRawEntries = []
for entry in os.scandir(rawPhotoFolder):
    rawName = entry.name.lower()
    if rawName.endswith(rawFileExt):
        rawName = rawName.replace(rawFileExt, '')
        if rawName not in refNames:
            deleteRawEntries.append(entry)
deleteRawEntries.sort(key=lambda x: x.name.lower())
print(f"Moving {len(deleteRawEntries)} RAW photos to {deleteFolder}")

# Move raw photos that don't have a matching reference photo to the delete subfolder
for entry in deleteRawEntries:
    oldPath = entry.path
    newPath = os.path.join(deleteFolder, entry.name)
    print(f"Moved {entry.name}")
    os.rename(oldPath, newPath)
