import os, platform
import json
import requests
import shutil
import subprocess  # 添加这个导入

from lib.GlobalCatalogFetcher import catalog_url
from lib.Il2CppInspectorDumper import Il2CppInspectorDumperCLI
from lib.FBSDumper import FbsDumperCLI

if __name__ == "__main__":
    # Setup paths
    os_system = platform.system()
    lib_dir = os.path.join(os.getcwd(), f'dump_lib')
    extract_dir = os.path.join(os.getcwd(), 'global_extracted')
    data_dir = os.path.join(os.getcwd(), 'global_data')

    libil2cpp_path = os.path.join(extract_dir, "config_arm64_v8a", "lib", "arm64-v8a", "libil2cpp.so")
    metadata_path = os.path.join(extract_dir, "BlueArchive_apk", "assets", "bin", "Data", "Managed", "Metadata", "global-metadata.dat")
    dummydll_dir = os.path.join(data_dir, "dll")
    
    il2cpp_exec_path = os.path.join(lib_dir, "Il2CppInspector", "Il2CppInspector.Redux.CLI")
    fbsdumper_exec_path = os.path.join(lib_dir, "FbsDumper", "FbsDumper")
    if os_system == "Windows":
        il2cpp_exec_path = os.path.join(lib_dir, "Il2CppInspector", "Il2CppInspector.Redux.CLI.exe")
        fbsdumper_exec_path = os.path.join(lib_dir, "FbsDumper", "FbsDumper.exe")

    os.makedirs(data_dir, exist_ok=True)

    # Dump il2cpp data from the apk file
    print("Dumping il2cpp data...")
    il2cppDumper = Il2CppInspectorDumperCLI(il2cpp_exec_path, libil2cpp_path, metadata_path)
    il2cppDumper.dump(data_dir)
    il2cppDumper.dump(os.path.join(data_dir, "ida_disassember"), use_dissambler=True, dissambler_option="IDA")
    # il2cppDumper.dump(os.path.join(data_dir, "ghidra_disassember"), use_dissambler=True, dissambler_option="Ghidra")

    # 新增：输出解密的 global-metadata.dat
    print("Outputting decrypted global-metadata.dat...")
    decrypted_metadata_path = os.path.join(data_dir, "decrypted-global-metadata.dat")
    
    cmd = [
        il2cpp_exec_path,
        "-i", libil2cpp_path,
        "-m", metadata_path,
        "--metadata-out", decrypted_metadata_path,
        "--select-outputs"  # 只输出 metadata，不生成其他文件
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Successfully decrypted metadata to: {decrypted_metadata_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error decrypting metadata: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    # Generate fbs both for V1 and V2
    print("Generating fbs...")
    fbsDumper = FbsDumperCLI(fbsdumper_exec_path, dummydll_dir, libil2cpp_path)
    fbsDumper.dump(data_dir, "V1", "BlueArchiveV1.fbs")
    fbsDumper.dump(data_dir, "V2", "BlueArchiveV2.fbs")

    # Copy assembly & metadata
    print("Copying assembly & metadata...")
    shutil.copy(libil2cpp_path, os.path.join(data_dir, "libil2cpp.so"))
    shutil.copy(metadata_path, os.path.join(data_dir, "global-metadata.dat"))

    # Old fbs generator
    # dump_cs_path = os.path.join(dumped_dir, "dump.cs")
    # fbs_path = os.path.join(dumped_dir, "BlueArchive.fbs")
    # FBSGenerator(dump_cs_path, fbs_path).generate_fbs()

    # Get the game url
    config_data = catalog_url()
    config_file_path = os.path.join(data_dir, 'config.json')
    resources_file_path = os.path.join(data_dir, 'resources.json')
    
    # Request the data from config and save to the disk
    try:
        response = requests.get(config_data['patch']['resource_path'])
        response.raise_for_status()
        resources_data = response.json()

        with open(config_file_path, 'w', encoding='utf-8') as file:
            json.dump(config_data, file, indent=4, ensure_ascii=False)
        with open(resources_file_path, 'w', encoding='utf-8') as file:
            json.dump(resources_data, file, indent=4, ensure_ascii=False)

        print(f"Config data has been written to {config_file_path}")
        print(f"Resources data has been written to {resources_file_path}")
    except requests.RequestException as e:
        print(f"Error fetching config data: {e}")

    print(f"Data has been moved to {data_dir}")