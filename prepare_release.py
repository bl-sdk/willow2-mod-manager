import os
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile


def create_release(release_path: str, mods_folder: str, sdk_files: List[str]) -> None:
    """
    Creates a release zip.

    Args:
        release_path: The path to the release zip.
        mods_folder: The path to the mods folder to include. Will be copied recursively.
        sdk_files: A list of paths to the SDK's files, which will be placed in Win32. Will not copy
                   folder structure.
    """
    zip_root = os.path.join("Binaries", "Win32")

    with ZipFile(release_path, "w", ZIP_DEFLATED, compresslevel=9) as zip_file:
        # Must always be placed in a folder called exactly 'Mods', regardless of where we're copying
        #  it from
        zipped_mods_root = os.path.join(zip_root, "Mods")

        for root, _, files in os.walk(mods_folder):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, mods_folder)
                zip_file.write(file_path, os.path.join(zipped_mods_root, rel_path))

        for file_path in sdk_files:
            file_name = os.path.basename(file_path)
            zip_file.write(file_path, os.path.join(zip_root, file_name))


if __name__ == "__main__":
    import traceback
    from argparse import ArgumentParser

    RELEASE_NAME = "PythonSDK.zip"
    MODS_FOLDER = "Mods"

    parser = ArgumentParser(description="Prepares a release zip. Copies the current Mods folder.")
    parser.add_argument(
        "sdk_files",
        nargs="+",
        help="The SDK's files, to be placed in Win32. Will not copy folder structure."
    )
    args = parser.parse_args()

    try:
        create_release(RELEASE_NAME, MODS_FOLDER, args.sdk_files)
    except Exception:
        traceback.print_exc()
        input("Press enter to exit")
