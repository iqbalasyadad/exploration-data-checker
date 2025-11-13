import os
import lasio
import segyio


# ===================== LAS FILE SCANNER (OOP) =====================

class LASFileScanner:
    """Handles finding and reading LAS files from directories"""
    
    def __init__(self, root_folder, filter_text="", filter_enabled=False):
        self.root_folder = root_folder
        self.filter_text = filter_text
        self.filter_enabled = filter_enabled
        self.las_files = []
    
    def find_all_las_files(self):
        """Recursively find all .las files in root folder"""
        self.las_files = []
        if not os.path.isdir(self.root_folder):
            return []
        
        for dirpath, dirnames, filenames in os.walk(self.root_folder):
            for filename in filenames:
                if filename.lower().endswith(".las"):
                    # Apply custom filter if enabled
                    if self.filter_enabled and self.filter_text:
                        if self.filter_text.upper() not in filename.upper():
                            continue
                    
                    full_path = os.path.join(dirpath, filename)
                    self.las_files.append(full_path)
        
        return self.las_files
    
    @staticmethod
    def read_las_file(filepath):
        """Safely read a LAS file and return lasio object"""
        try:
            las = lasio.read(filepath)
            if not hasattr(las, "curves") or len(las.curves) == 0:
                print(f"File {filepath} has no curves or invalid LAS format")
                return None
            return las
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")
            return None

# ===================== SEGY FILE SCANNER (OOP) =====================

class SEGYFileScanner:
    """Handles finding and reading SEGY files from directories"""
    
    def __init__(self, root_folder, filter_text="", filter_enabled=False):
        self.root_folder = root_folder
        self.filter_text = filter_text
        self.filter_enabled = filter_enabled
        self.segy_files = []
    
    def find_all_segy_files(self):
        """Recursively find all .sgy/.segy files in root folder"""
        self.segy_files = []
        if not os.path.isdir(self.root_folder):
            return []
        
        for dirpath, dirnames, filenames in os.walk(self.root_folder):
            for filename in filenames:
                if filename.lower().endswith((".sgy", ".segy")):
                    if self.filter_enabled and self.filter_text:
                        if self.filter_text.upper() not in filename.upper():
                            continue
                    
                    full_path = os.path.join(dirpath, filename)
                    self.segy_files.append(full_path)
        
        return self.segy_files
    
    @staticmethod
    def read_segy_file(filepath, mode):
        """Safely read a SEGY file and return segyio object"""
        try:
            if mode=='2D':
                segy = segyio.open(filepath, ignore_geometry=True)
            elif mode=='3D':
                segy = segyio.open(filepath, "r", ignore_geometry=False, strict=False)
                segy.mmap()
            return segy
        except Exception as e:
            print(f"Failed to read {filepath}: {e}")
            return None