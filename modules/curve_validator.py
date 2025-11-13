import numpy as np

# ===================== CURVE VALIDATOR (OOP) =====================

class CurveValidator:
    """Validates log curves against defined criteria"""
    
    def __init__(self, curve_config, null_value=-999.25):
        self.curve_config = curve_config
        self.null_value = null_value
    
    def update_config(self, new_config):
        """Update the curve configuration"""
        self.curve_config = new_config
    
    def validate_las_file(self, las):
        """Validate all curves in a LAS file against configuration"""
        available_curves = {c.mnemonic.upper(): c for c in las.curves}
        results = {}
        
        for key, info in self.curve_config.items():
            found_alias = self._find_curve_alias(info["aliases"], available_curves)
            
            if not found_alias:
                results[key] = {"status": "N", "reason": "Not found"}
                continue
            
            is_valid, reason = self._validate_curve_data(las, found_alias, info)
            results[key] = {
                "status": "Y" if is_valid else "N",
                "reason": reason
            }
        
        return results
    
    def get_detailed_curve_info(self, las):
        """Get detailed information for all configured curves"""
        available_curves = {c.mnemonic.upper(): c for c in las.curves}
        detailed_info = {}
        
        for key, info in self.curve_config.items():
            found_alias = self._find_curve_alias(info["aliases"], available_curves)
            
            if not found_alias:
                detailed_info[key] = {
                    "found": False,
                    "mnemonic": "N/A",
                    "min": "N/A",
                    "max": "N/A",
                    "percent_filled": "N/A",
                    "unit": "N/A",
                    "description": info["description"]
                }
                continue
            
            try:
                data = np.array(las[found_alias], dtype=float)
                valid_mask = data != self.null_value
                valid_data = data[valid_mask]
                
                total_points = len(data)
                valid_points = len(valid_data)
                percent_filled = (valid_points / total_points * 100) if total_points > 0 else 0
                
                min_val = float(np.nanmin(valid_data)) if valid_data.size > 0 else None
                max_val = float(np.nanmax(valid_data)) if valid_data.size > 0 else None
                
                # Get unit from curve
                curve_obj = las.curves[found_alias]
                unit = curve_obj.unit if hasattr(curve_obj, 'unit') and curve_obj.unit else "N/A"
                
                detailed_info[key] = {
                    "found": True,
                    "mnemonic": found_alias,
                    "min": f"{min_val:.4f}" if min_val is not None else "N/A",
                    "max": f"{max_val:.4f}" if max_val is not None else "N/A",
                    "percent_filled": f"{percent_filled:.2f}",
                    "unit": unit,
                    "description": info["description"]
                }
            except Exception as e:
                detailed_info[key] = {
                    "found": True,
                    "mnemonic": found_alias,
                    "min": "Error",
                    "max": "Error",
                    "percent_filled": "Error",
                    "unit": "N/A",
                    "description": info["description"]
                }
        
        return detailed_info
    
    @staticmethod
    def get_well_name_from_las(las):
        """Extract well name from LAS file header"""
        try:
            # Try common well name fields in LAS header
            if hasattr(las, 'well') and hasattr(las.well, 'WELL'):
                well_name = las.well.WELL.value
                if well_name and str(well_name).strip():
                    return str(well_name).strip()
            
            # Alternative field names
            if hasattr(las, 'well'):
                for field in ['UWI', 'API', 'WELLNAME', 'NAME']:
                    if hasattr(las.well, field):
                        value = getattr(las.well, field).value
                        if value and str(value).strip():
                            return str(value).strip()
            
            return "N/A"
        except:
            return "N/A"
    
    @staticmethod
    def get_depth_info_from_las(las):
        """Extract depth information from LAS file"""
        try:
            depth_info = {
                'depth_unit': 'N/A',
                'pd': 'N/A',
                'epd': 'N/A',
                'ekb': 'N/A',
                'egl': 'N/A',
                'lmf': 'N/A',
                'elz': 'N/A',
                'start': 'N/A',
                'stop': 'N/A',
                'step': 'N/A'
            }
            
            # Get start, stop, step from well section
            if hasattr(las, 'well'):
                if hasattr(las.well, 'STRT'):
                    depth_info['start'] = f"{las.well.STRT.value:.2f}"
                if hasattr(las.well, 'STOP'):
                    depth_info['stop'] = f"{las.well.STOP.value:.2f}"
                if hasattr(las.well, 'STEP'):
                    depth_info['step'] = f"{las.well.STEP.value:.2f}"

                # Get depth unit
                if hasattr(las.well, 'STRT') and hasattr(las.well.STRT, 'unit'):
                    depth_info['depth_unit'] = str(las.well.STRT.unit) if las.well.STRT.unit else 'N/A'

                # Log Measured From (LMF)
                if hasattr(las.well, 'LMF'):
                    depth_info['lmf'] = f"{las.well.LMF.value:}"

                # Elevation Log Zero (ELZ)
                for field in ['ELZ']:
                    if hasattr(las.well, field):
                        value = getattr(las.well, field).value
                        if value is not None:
                            depth_info['elz'] = f"{float(value):.2f}"
                            break

                # Permanent Datum (PD)
                if hasattr(las.well, 'PD'):
                    depth_info['pd'] = f"{las.well.PD.value:}"

                for field in ['EPD']:
                    if hasattr(las.well, field):
                        value = getattr(las.well, field).value
                        if value is not None:
                            depth_info['epd'] = f"{float(value):.2f}"
                            break
                
                # Kelly Bushing (KB)
                for field in ['KB', 'EKB', 'EKBD', 'EDF']:
                    if hasattr(las.well, field):
                        value = getattr(las.well, field).value
                        if value is not None:
                            depth_info['ekb'] = f"{float(value):.2f}"
                            break
                
                # Ground Level (GL)
                for field in ['GL', 'GLE', 'GLELEV', 'EGL']:
                    if hasattr(las.well, field):
                        value = getattr(las.well, field).value
                        if value is not None:
                            depth_info['egl'] = f"{float(value):.2f}"
                            break

            
            return depth_info
        except Exception as e:
            return {
                'depth_unit': 'Error',
                'pd': 'Error',
                'epd': 'Error',
                'ekb': 'Error',
                'egl': 'Error',
                'lmf': 'Error',
                'elz': 'Error',
                'start': 'Error',
                'stop': 'Error',
                'step': 'Error',
            }
    
    def _find_curve_alias(self, aliases, available_curves):
        """Find the first matching alias in available curves"""
        for alias in aliases:
            if alias.upper() in available_curves:
                return alias.upper()
        return None
    
    def _validate_curve_data(self, las, curve_name, curve_info):
        """Validate individual curve data - checks existence and valid data only"""
        try:
            data = np.array(las[curve_name], dtype=float)
            valid_mask = data != self.null_value
            valid_data = data[valid_mask]
            
            if valid_data.size == 0:
                return False, "No valid data"
            
            min_val = float(np.nanmin(valid_data))
            max_val = float(np.nanmax(valid_data))
            
            # Only return the range, no validation against valid_range
            return True, f"Valid ({min_val:.2f}-{max_val:.2f})"
        
        except Exception as e:
            return False, f"Error: {str(e)}"