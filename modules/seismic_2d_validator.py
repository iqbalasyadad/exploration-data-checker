import os
import numpy as np
import segyio
import re

# ===================== SEISMIC 2D VALIDATOR (ENHANCED) =====================

class Seismic2DValidator:
    """Validates and analyzes seismic 2D data with comprehensive QC metrics"""
    
    def __init__(self):
        self.qc_config = {
            "format": "SEGY Format Version",
            "traces": "Number of Traces",
            "samples": "Samples per Trace",
            "sample_interval": "Sample Interval (ms)",
            "trace_length": "Trace Length (ms)",
            "amplitude": "Amplitude Range",
            "null_traces": "Null/Dead Traces",
            "sorting": "Trace Sorting Code"
        }
    
    def get_basic_info(self, segy):
        """Get basic information for table display"""
        info = {}
        
        try:
            info["filename"] = os.path.basename(segy._filename) if hasattr(segy, '_filename') else "N/A"
            info["line_name"] = self._extract_line_name(segy)
            info["trace_count"] = segy.tracecount
            info["sample_count"] = segy.samples.size
            
            interval = segy.bin[segyio.BinField.Interval] / 1000.0
            info["sample_interval"] = f"{interval:.2f}"
            
            trace_length = (segy.samples.size - 1) * interval
            info["trace_length"] = f"{trace_length:.0f}"
            
            format_code = segy.bin[segyio.BinField.Format]
            info["format"] = self._get_format_short(format_code)
            
            info["cdp_range"] = self._get_cdp_range(segy)
            
        except Exception as e:
            info["error"] = str(e)
        
        return info


    def get_comprehensive_info(self, segy):
        """Get comprehensive seismic information for detailed display"""
        info = {}
        
        try:
            # Basic file information
            info["Filename"] = os.path.basename(segy._filename) if hasattr(segy, '_filename') else "N/A"
            info["Line Name"] = self._extract_line_name(segy)
            
            # Format information
            format_code = segy.bin[segyio.BinField.Format]
            info["Format"] = self._get_format_description(format_code)
            
            # Trace and sample information
            info["Trace Count"] = str(segy.tracecount)
            info["Samples per Trace"] = str(segy.samples.size)
            
            interval = segy.bin[segyio.BinField.Interval] / 1000.0
            info["Sample Interval (ms)"] = f"{interval:.3f}"
            
            # CDP Range
            info["CDP Range"] = self._get_cdp_range(segy)
            
            # Coordinate Range (X and Y)
            coord_info = self._get_coordinate_range(segy)
            info["Coordinate Range X"] = coord_info["x_range"]
            info["Coordinate Range Y"] = coord_info["y_range"]
            
            # Amplitude statistics
            amp_stats = self._calculate_amplitude_stats(segy)
            info["Amplitude Range"] = f"{amp_stats['min']:.4f} to {amp_stats['max']:.4f}"
            info["RMS Amplitude"] = f"{amp_stats['rms']:.4f}"
            
            # Frequency analysis
            freq_info = self._calculate_frequency_metrics(segy, interval)
            info["Nyquist Frequency"] = f"{freq_info['nyquist']:.2f} Hz"
            info["Dominant Frequency"] = f"{freq_info['dominant']:.2f} Hz"
            
            # Null/Dead traces
            null_info = self._analyze_null_traces(segy)
            info["Null/Dead Traces"] = f"{null_info['count']} ({null_info['percent']:.2f}%)"
            
            # Trace length uniformity
            uniformity = self._check_trace_length_uniformity(segy)
            info["Trace Length Uniformity"] = uniformity
            
            # Clipping detection
            clipping = self._detect_clipping(segy, amp_stats)
            info["Clipping Detected"] = clipping
            
            # Trace spacing analysis
            spacing_info = self._calculate_trace_spacing(segy)
            info["Average Trace Spacing (m)"] = spacing_info["average"]
            info["Min Trace Spacing (m)"] = spacing_info["min"]
            info["Max Trace Spacing (m)"] = spacing_info["max"]

            
            # Line geometry
            geometry_info = self._calculate_line_geometry(segy)
            info["Straight Line Distance (m)"] = geometry_info["straight_distance"]
            info["Est. Total Line Length (km)"] = geometry_info["total_length"]
            info["Line Sinuosity"] = geometry_info["sinuosity"]
            info["Line Shape"] = geometry_info["shape"]
            info["Coordinate Order"] = geometry_info["order"]
            
            # Binary header information
            binary_info = self._get_binary_header_info(segy)
            info["Binary"] = binary_info["binary"]
            info["Format Code"] = binary_info["format_code"]
            info["Trace Sorting"] = binary_info["sorting"]
            info["Endian Type"] = binary_info["endian"]
            info["Measurement System"] = binary_info["measurement_system"]
            
            # Signal statistics
            signal_stats = self._calculate_signal_statistics(segy)
            info["Signal Std Dev"] = f"{signal_stats['std_dev']:.4f}"
            info["Signal Mean"] = f"{signal_stats['mean']:.4f}"
            info["Skewness"] = f"{signal_stats['skewness']:.4f}"
            info["Kurtosis"] = f"{signal_stats['kurtosis']:.4f}"
            info["Est. SNR (dB)"] = f"{signal_stats['snr']:.2f}"
            
        except Exception as e:
            info["Error"] = f"Error extracting comprehensive info: {str(e)}"
        
        return info
    
    # ==================== COORDINATE ANALYSIS ====================
    
    def _get_coordinate_range(self, segy):
        """Get X and Y coordinate ranges (auto-detect valid coordinate fields)"""
        try:
            coord_candidates = [
                (segyio.TraceField.CDP_X, segyio.TraceField.CDP_Y),
                (segyio.TraceField.SourceX, segyio.TraceField.SourceY),
                (segyio.TraceField.GroupX, segyio.TraceField.GroupY)
            ]

            chosen_fields = None

            # Find which coordinate pair has valid non-zero values
            for x_field, y_field in coord_candidates:
                sample_check = []
                for i in range(min(50, segy.tracecount)):
                    h = segy.header[i]
                    x, y = h.get(x_field, 0), h.get(y_field, 0)
                    if (x != 0 or y != 0) and not np.isnan(x) and not np.isnan(y):
                        sample_check.append((x, y))
                if len(sample_check) > 5:
                    chosen_fields = (x_field, y_field)
                    break

            if not chosen_fields:
                return {"x_range": "No valid coordinates", "y_range": "No valid coordinates"}

            x_field, y_field = chosen_fields

            x_coords, y_coords = [], []
            sample_size = min(200, segy.tracecount)
            indices = np.linspace(0, segy.tracecount - 1, sample_size, dtype=int)

            for idx in indices:
                h = segy.header[int(idx)]
                x, y = h.get(x_field, 0), h.get(y_field, 0)
                if (x != 0 or y != 0) and not np.isnan(x) and not np.isnan(y):
                    x_coords.append(x)
                    y_coords.append(y)

            if x_coords and y_coords:
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                return {
                    "x_range": f"{x_min:.2f} to {x_max:.2f}",
                    "y_range": f"{y_min:.2f} to {y_max:.2f}"
                }
            else:
                return {"x_range": "No valid coordinates", "y_range": "No valid coordinates"}

        except Exception as e:
            return {"x_range": "Error", "y_range": "Error"}

    
    # ==================== AMPLITUDE ANALYSIS ====================
    
    def _calculate_amplitude_stats(self, segy, sample_size=100):
        """Calculate comprehensive amplitude statistics"""
        try:
            trace_count = min(sample_size, segy.tracecount)
            indices = np.linspace(0, segy.tracecount-1, trace_count, dtype=int)
            
            all_samples = []
            for idx in indices:
                trace = segy.trace[idx]
                all_samples.extend(trace)
            
            all_samples = np.array(all_samples)
            
            # Remove NaN and inf values
            all_samples = all_samples[np.isfinite(all_samples)]
            
            rms = np.sqrt(np.mean(all_samples**2)) if len(all_samples) > 0 else 0
            
            return {
                'min': float(np.min(all_samples)) if len(all_samples) > 0 else 0,
                'max': float(np.max(all_samples)) if len(all_samples) > 0 else 0,
                'mean': float(np.mean(all_samples)) if len(all_samples) > 0 else 0,
                'std': float(np.std(all_samples)) if len(all_samples) > 0 else 0,
                'rms': float(rms)
            }
        except Exception as e:
            return {'min': 0, 'max': 0, 'mean': 0, 'std': 0, 'rms': 0}
    
    # ==================== FREQUENCY ANALYSIS ====================
    
    def _calculate_frequency_metrics(self, segy, sample_interval_ms):
        """Calculate frequency-related metrics"""
        try:
            # Nyquist frequency
            dt_seconds = sample_interval_ms / 1000.0
            nyquist = 1.0 / (2.0 * dt_seconds)
            
            # Estimate dominant frequency from a sample trace
            sample_trace_idx = segy.tracecount // 2
            trace_data = segy.trace[sample_trace_idx]
            
            # Remove mean
            trace_data = trace_data - np.mean(trace_data)
            
            # Apply FFT
            fft_result = np.fft.rfft(trace_data)
            fft_freq = np.fft.rfftfreq(len(trace_data), d=dt_seconds)
            
            # Get magnitude spectrum
            magnitude = np.abs(fft_result)
            
            # Find dominant frequency (peak in spectrum)
            dominant_idx = np.argmax(magnitude[1:]) + 1  # Skip DC component
            dominant_freq = fft_freq[dominant_idx]
            
            return {
                'nyquist': nyquist,
                'dominant': dominant_freq
            }
        except Exception as e:
            return {'nyquist': 0, 'dominant': 0}
    
    # ==================== TRACE ANALYSIS ====================
    
    def _analyze_null_traces(self, segy, sample_size=100):
        """Analyze null/dead traces with percentage"""
        try:
            trace_count = min(sample_size, segy.tracecount)
            indices = np.linspace(0, segy.tracecount-1, trace_count, dtype=int)
            
            null_count = 0
            for idx in indices:
                trace = segy.trace[idx]
                if np.all(trace == 0) or np.all(np.isnan(trace)) or np.std(trace) < 1e-10:
                    null_count += 1
            
            estimated_null = int((null_count / trace_count) * segy.tracecount)
            null_percent = (estimated_null / segy.tracecount * 100) if segy.tracecount > 0 else 0
            
            return {
                'count': estimated_null,
                'percent': null_percent
            }
        except Exception as e:
            return {'count': 0, 'percent': 0}
    
    def _check_trace_length_uniformity(self, segy):
        """Check if all traces have uniform length"""
        try:
            # In SEG-Y, all traces should have same length
            # Check a few traces to verify
            sample_size = min(10, segy.tracecount)
            indices = np.linspace(0, segy.tracecount-1, sample_size, dtype=int)
            
            lengths = set()
            for idx in indices:
                trace = segy.trace[idx]
                lengths.add(len(trace))
            
            if len(lengths) == 1:
                return "Uniform"
            else:
                return f"Non-uniform ({len(lengths)} different lengths)"
                
        except Exception as e:
            return "Error checking uniformity"
    
    def _detect_clipping(self, segy, amp_stats, sample_size=50):
        """Detect if signal clipping is present"""
        try:
            trace_count = min(sample_size, segy.tracecount)
            indices = np.linspace(0, segy.tracecount-1, trace_count, dtype=int)
            
            max_amp = amp_stats['max']
            min_amp = amp_stats['min']
            
            clipped_samples = 0
            total_samples = 0
            
            # Define clipping threshold (samples at exactly min or max)
            for idx in indices:
                trace = segy.trace[idx]
                total_samples += len(trace)
                
                # Count samples at extremes
                clipped_samples += np.sum(np.abs(trace - max_amp) < 1e-6)
                clipped_samples += np.sum(np.abs(trace - min_amp) < 1e-6)
            
            clip_percent = (clipped_samples / total_samples * 100) if total_samples > 0 else 0
            
            if clip_percent > 1.0:
                return f"Yes ({clip_percent:.2f}%)"
            else:
                return "No"
                
        except Exception as e:
            return "Error"
    
    # ==================== GEOMETRY ANALYSIS ====================
    
    def _calculate_trace_spacing(self, segy):
        """Calculate trace spacing statistics with coordinate field auto-detection"""
        try:
            coord_candidates = [
                (segyio.TraceField.CDP_X, segyio.TraceField.CDP_Y),
                (segyio.TraceField.SourceX, segyio.TraceField.SourceY),
                (segyio.TraceField.GroupX, segyio.TraceField.GroupY)
            ]

            chosen_fields = None

            # Detect which coordinate pair has valid data
            for x_field, y_field in coord_candidates:
                valid_coords = 0
                for i in range(min(50, segy.tracecount)):
                    h = segy.header[i]
                    x, y = h.get(x_field, 0), h.get(y_field, 0)
                    if (x != 0 or y != 0) and not np.isnan(x) and not np.isnan(y):
                        valid_coords += 1
                if valid_coords > 5:
                    chosen_fields = (x_field, y_field)
                    break

            if not chosen_fields:
                return {'average': "No valid coordinates", 'min': "No valid coordinates", 'max': "No valid coordinates"}

            x_field, y_field = chosen_fields

            # Sample subset for performance
            sample_size = min(200, segy.tracecount - 1)
            indices = np.linspace(0, segy.tracecount - 2, sample_size, dtype=int)

            spacings = []
            for idx in indices:
                h1 = segy.header[int(idx)]
                h2 = segy.header[int(idx) + 1]
                x1, y1 = h1.get(x_field, 0), h1.get(y_field, 0)
                x2, y2 = h2.get(x_field, 0), h2.get(y_field, 0)

                # Only include valid pairs
                if (x1 != 0 or y1 != 0) and (x2 != 0 or y2 != 0) and not np.isnan(x1) and not np.isnan(y1):
                    distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    if distance > 0:
                        spacings.append(distance)

            if spacings:
                avg_spacing = np.mean(spacings)
                min_spacing = np.min(spacings)
                max_spacing = np.max(spacings)
                return {
                    'average': f"{avg_spacing:.2f}",
                    'min': f"{min_spacing:.2f}",
                    'max': f"{max_spacing:.2f}"
                }
            else:
                return {'average': "No valid coordinates", 'min': "No valid coordinates", 'max': "No valid coordinates"}

        except Exception:
            return {'average': "Error", 'min': "Error", 'max': "Error"}

    
    def _calculate_line_geometry(self, segy):
        """Calculate line geometry metrics with coordinate fallback and validation"""
        try:
            # Possible coordinate field pairs in SEG-Y
            coord_candidates = [
                (segyio.TraceField.CDP_X, segyio.TraceField.CDP_Y),
                (segyio.TraceField.SourceX, segyio.TraceField.SourceY),
                (segyio.TraceField.GroupX, segyio.TraceField.GroupY)
            ]
            
            # Detect which pair actually contains valid coordinates
            chosen_fields = None
            for x_field, y_field in coord_candidates:
                sample_check = []
                for i in range(min(50, segy.tracecount)):
                    h = segy.header[i]
                    x, y = h.get(x_field, 0), h.get(y_field, 0)
                    if (x != 0 or y != 0) and not np.isnan(x) and not np.isnan(y):
                        sample_check.append((x, y))
                if len(sample_check) > 5:  # found enough valid coordinates
                    chosen_fields = (x_field, y_field)
                    break
            
            if not chosen_fields:
                return {
                    'straight_distance': "No coordinates found",
                    'total_length': "No coordinates found",
                    'sinuosity': "N/A",
                    'shape': "Unknown",
                    'order': "Unknown"
                }

            x_field, y_field = chosen_fields

            # Collect coordinates across the line
            coords = []
            sample_size = min(200, segy.tracecount)
            indices = np.linspace(0, segy.tracecount - 1, sample_size, dtype=int)
            
            for idx in indices:
                h = segy.header[int(idx)]
                x = h.get(x_field, 0)
                y = h.get(y_field, 0)
                if (x != 0 or y != 0) and not np.isnan(x) and not np.isnan(y):
                    coords.append((x, y))
            
            if len(coords) < 2:
                return {
                    'straight_distance': "Insufficient coordinates",
                    'total_length': "Insufficient coordinates",
                    'sinuosity': "N/A",
                    'shape': "Unknown",
                    'order': "Unknown"
                }

            # Compute straight distance (first to last)
            straight_dist = np.sqrt(
                (coords[-1][0] - coords[0][0]) ** 2 +
                (coords[-1][1] - coords[0][1]) ** 2
            )

            # Compute total distance (sum of all segments)
            segment_lengths = np.sqrt(np.sum(np.diff(coords, axis=0) ** 2, axis=1))
            total_length = np.sum(segment_lengths)

            sinuosity = total_length / straight_dist if straight_dist > 0 else 1.0

            # Determine shape classification
            if sinuosity < 1.05:
                shape = "Straight"
            elif sinuosity < 1.2:
                shape = "Nearly Straight"
            elif sinuosity < 1.5:
                shape = "Curved"
            else:
                shape = "Highly Curved"

            # Determine coordinate order
            x_coords = [c[0] for c in coords]
            y_coords = [c[1] for c in coords]
            x_increasing = all(x_coords[i] <= x_coords[i + 1] for i in range(len(x_coords) - 1))
            x_decreasing = all(x_coords[i] >= x_coords[i + 1] for i in range(len(x_coords) - 1))
            y_increasing = all(y_coords[i] <= y_coords[i + 1] for i in range(len(y_coords) - 1))
            y_decreasing = all(y_coords[i] >= y_coords[i + 1] for i in range(len(y_coords) - 1))

            if x_increasing or x_decreasing or y_increasing or y_decreasing:
                order = "Sequential"
            else:
                order = "Irregular"

            return {
                'straight_distance': f"{straight_dist:.2f}",
                'total_length': f"{total_length / 1000:.3f}",  # km
                'sinuosity': f"{sinuosity:.3f}",
                'shape': shape,
                'order': order
            }

        except Exception as e:
            return {
                'straight_distance': "Error",
                'total_length': "Error",
                'sinuosity': "Error",
                'shape': "Error",
                'order': "Error"
            }

    
    # ==================== BINARY HEADER ANALYSIS ====================
    
    def _get_binary_header_info(self, segy):
        """Extract binary header information"""
        try:
            format_code = segy.bin[segyio.BinField.Format]
            sorting_code = segy.bin[segyio.BinField.SortingCode]
            
            # Try to detect endianness
            try:
                # Check if binary header values make sense
                interval = segy.bin[segyio.BinField.Interval]
                if 100 <= interval <= 100000:  # Reasonable range for microseconds
                    endian = "Little Endian"
                else:
                    endian = "Big Endian (possible)"
            except:
                endian = "Unknown"
            
            # Get measurement system
            try:
                meas_system = segy.bin[segyio.BinField.MeasurementSystem]
                if meas_system == 1:
                    measurement = "Meters"
                elif meas_system == 2:
                    measurement = "Feet"
                else:
                    measurement = f"Unknown ({meas_system})"
            except:
                measurement = "Unknown"
            
            return {
                'binary': "SEG-Y Rev 1",
                'format_code': f"{format_code} ({self._get_format_short(format_code)})",
                'sorting': self._get_sorting_description(sorting_code),
                'endian': endian,
                'measurement_system': measurement
            }
            
        except Exception as e:
            return {
                'binary': "Error",
                'format_code': "Error",
                'sorting': "Error",
                'endian': "Error",
                'measurement_system': "Error"
            }
    
    # ==================== SIGNAL STATISTICS ====================
    
    def _calculate_signal_statistics(self, segy, sample_size=100):
        """Calculate advanced signal statistics"""
        try:
            trace_count = min(sample_size, segy.tracecount)
            indices = np.linspace(0, segy.tracecount-1, trace_count, dtype=int)
            
            all_samples = []
            for idx in indices:
                trace = segy.trace[idx]
                all_samples.extend(trace)
            
            all_samples = np.array(all_samples)
            all_samples = all_samples[np.isfinite(all_samples)]
            
            if len(all_samples) == 0:
                return {
                    'std_dev': 0, 'mean': 0, 'skewness': 0, 
                    'kurtosis': 0, 'snr': 0
                }
            
            # Basic statistics
            mean = np.mean(all_samples)
            std_dev = np.std(all_samples)
            
            # Skewness (measure of asymmetry)
            skewness = np.mean(((all_samples - mean) / std_dev) ** 3) if std_dev > 0 else 0
            
            # Kurtosis (measure of tailedness)
            kurtosis = np.mean(((all_samples - mean) / std_dev) ** 4) - 3 if std_dev > 0 else 0
            
            # Estimate SNR (Signal to Noise Ratio)
            # Using RMS of signal vs RMS of noise (estimated from high-frequency component)
            signal_rms = np.sqrt(np.mean(all_samples**2))
            
            # Estimate noise from differences between adjacent samples
            noise_estimate = np.diff(all_samples)
            noise_rms = np.sqrt(np.mean(noise_estimate**2))
            
            snr_linear = signal_rms / noise_rms if noise_rms > 0 else 1
            snr_db = 20 * np.log10(snr_linear) if snr_linear > 0 else 0
            
            return {
                'std_dev': float(std_dev),
                'mean': float(mean),
                'skewness': float(skewness),
                'kurtosis': float(kurtosis),
                'snr': float(snr_db)
            }
            
        except Exception as e:
            return {
                'std_dev': 0, 'mean': 0, 'skewness': 0, 
                'kurtosis': 0, 'snr': 0
            }
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _extract_line_name(segy):
        try:
            text_header = segyio.tools.wrap(segy.text[0])
            for line in text_header.splitlines():
                match = re.search(r'LINE\s*[:\-]?\s*(\S+)', line.upper())
                if match:
                    return match.group(1)
            return "N/A"
        except:
            return "N/A"
    
    def _get_cdp_range(self, segy):
        try:
            first_cdp = segy.header[0][segyio.TraceField.CDP]
            last_cdp = segy.header[segy.tracecount-1][segyio.TraceField.CDP]
            
            if first_cdp == 0 and last_cdp == 0:
                first_sp = segy.header[0][segyio.TraceField.FieldRecord]
                last_sp = segy.header[segy.tracecount-1][segyio.TraceField.FieldRecord]
                return f"{first_sp} - {last_sp}"
            else:
                return f"{first_cdp} - {last_cdp}"
        except:
            return "N/A"
    
    @staticmethod
    def _get_format_short(format_code):
        formats = {
            1: "IBM Float",
            2: "4-byte Int",
            3: "2-byte Int",
            5: "IEEE Float",
            8: "1-byte Int"
        }
        return formats.get(format_code, f"Code {format_code}")
    
    @staticmethod
    def _get_format_description(format_code):
        formats = {
            1: "4-byte IBM floating-point",
            2: "4-byte signed integer",
            3: "2-byte signed integer",
            5: "4-byte IEEE floating-point",
            8: "1-byte signed integer"
        }
        return formats.get(format_code, f"Unknown ({format_code})")
    
    @staticmethod
    def _get_sorting_description(sorting_code):
        sorting = {
            -1: "Other",
            0: "Unknown",
            1: "As recorded (no sorting)",
            2: "CDP ensemble",
            3: "Single fold continuous profile",
            4: "Horizontally stacked",
            5: "Common source point",
            6: "Common receiver point",
            7: "Common offset point",
            8: "Common mid-point",
            9: "Common conversion point"
        }
        return sorting.get(sorting_code, f"Unknown ({sorting_code})")