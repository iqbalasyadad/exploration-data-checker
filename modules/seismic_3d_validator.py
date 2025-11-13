import os
import numpy as np
import segyio


# ===================== SEISMIC 3D VALIDATOR (ENHANCED) =====================

class Seismic3DValidator:
    """Validates and extracts comprehensive QC information from 3D seismic data"""
    
    def __init__(self):
        self.qc_config = {
            "format": "SEGY Format Version",
            "traces": "Total Traces",
            "samples": "Samples per Trace",
            "sample_interval": "Sample Interval (ms)",
            "trace_length": "Trace Length (ms)",
            "amplitude": "Amplitude Range",
            "null_traces": "Null/Dead Traces",
            "geometry": "3D Geometry",
            "inline_range": "Inline Range",
            "crossline_range": "Crossline Range"
        }
    
    def get_comprehensive_info(self, segy):
        """Get comprehensive QC information from 3D SEGY file"""
        qc_info = {}
        
        # try:
        #     with segyio.open(filepath, "r", ignore_geometry=False, strict=False) as segy:
        #         segy.mmap()
                
        #         # Basic Information
        #         qc_info.update(self._extract_basic_info(segy, filepath))
                
        #         # 3D Geometry
        #         qc_info.update(self._extract_3d_geometry(segy))
                
        #         # Signal Analysis
        #         qc_info.update(self._extract_signal_info(segy))
                
        #         # Trace Quality
        #         qc_info.update(self._extract_trace_quality(segy))
                
        #         # Binary Header
        #         qc_info.update(self._extract_binary_header(segy))
                
        #         # Volume Statistics
        #         qc_info.update(self._extract_volume_stats(segy))

        try:    
            # Basic Information
            qc_info.update(self._extract_basic_info(segy))
            
            # 3D Geometry
            qc_info.update(self._extract_3d_geometry(segy))
            
            # Signal Analysis
            qc_info.update(self._extract_signal_info(segy))
            
            # Trace Quality
            qc_info.update(self._extract_trace_quality(segy))
            
            # Binary Header
            qc_info.update(self._extract_binary_header(segy))
            
            # Volume Statistics
            qc_info.update(self._extract_volume_stats(segy))
                
        except Exception as e:
            qc_info["Error"] = str(e)
        
        return qc_info
    
    def _extract_basic_info(self, segy):
        """Extract basic file information"""
        info = {}
        try:
            # info["Filename"] = os.path.basename(filepath)
            # info["Survey Name"] = self._extract_survey_name(segy)
            # info["Full Path"] = filepath
            info["Filename"] = os.path.basename(segy._filename) if hasattr(segy, '_filename') else "N/A"
            info["Total Traces"] = str(segy.tracecount)
            
            try:
                samples_per_trace = len(segy.samples)
            except:
                samples_per_trace = segy.bin[segyio.BinField.Samples]
            info["Samples per Trace"] = str(samples_per_trace)
            
            # Sample interval
            dt_microsec = segyio.dt(segy)
            sample_interval_ms = dt_microsec / 1000.0
            info["Sample Interval (ms)"] = f"{sample_interval_ms:.3f}"
            
            # Trace length
            trace_length_ms = samples_per_trace * sample_interval_ms
            if trace_length_ms > 10000:
                info["Trace Length (s)"] = f"{trace_length_ms / 1000:.3f}"
            else:
                info["Trace Length (ms)"] = f"{trace_length_ms:.2f}"
            
            # Time Range
            info["Time Range"] = f"0 - {trace_length_ms:.2f} ms"
            
            # Data Format
            format_code = segy.format
            info["Data Format"] = self._get_format_description(format_code)
            
            # Sorting
            try:
                sorting_code = segy.bin[segyio.BinField.SortingCode]
                info["Sorting"] = self._get_sorting_description(sorting_code)
            except:
                info["Sorting"] = "Not available"
                
        except Exception as e:
            info["Basic Info Error"] = str(e)
        
        return info
    
    def _extract_3d_geometry(self, segy):
        """Extract 3D geometry information"""
        info = {}
        try:
            # Inline Range
            try:
                ilines = list(segy.ilines)
                if ilines:
                    info["Inline Range"] = f"{min(ilines)} - {max(ilines)}"
                else:
                    info["Inline Range"] = "Not available"
            except:
                info["Inline Range"] = "Not available"
            
            # Crossline Range
            try:
                xlines = list(segy.xlines)
                if xlines:
                    info["Crossline Range"] = f"{min(xlines)} - {max(xlines)}"
                else:
                    info["Crossline Range"] = "Not available"
            except:
                info["Crossline Range"] = "Not available"
            
            # Inline Spacing
            try:
                ilines = list(segy.ilines)
                if len(ilines) > 1:
                    il_spacing = ilines[1] - ilines[0]
                    info["Inline Spacing"] = f"{il_spacing}"
                else:
                    info["Inline Spacing"] = "N/A"
            except:
                info["Inline Spacing"] = "Not available"
            
            # Crossline Spacing
            try:
                xlines = list(segy.xlines)
                if len(xlines) > 1:
                    xl_spacing = xlines[1] - xlines[0]
                    info["Crossline Spacing"] = f"{xl_spacing}"
                else:
                    info["Crossline Spacing"] = "N/A"
            except:
                info["Crossline Spacing"] = "Not available"
                
        except Exception as e:
            info["3D Geometry Error"] = str(e)
        
        return info
    
    def _extract_signal_info(self, segy):
        """Extract signal characteristics"""
        info = {}
        try:
            n_traces = segy.tracecount
            sample_size = min(100, n_traces)
            step = max(1, n_traces // sample_size)
            
            traces = []
            for i in range(0, n_traces, step):
                if len(traces) >= sample_size:
                    break
                traces.append(segy.trace[i])
            traces = np.array(traces)
            
            # Amplitude statistics
            info["Amplitude Range"] = f"{np.nanmin(traces):.2e} to {np.nanmax(traces):.2e}"
            info["Amplitude Mean"] = f"{np.nanmean(traces):.2e}"
            info["Amplitude Std Dev"] = f"{np.nanstd(traces):.2e}"
            
            # Frequency Analysis
            dt = segyio.dt(segy) * 1e-6
            nyquist = 1 / (2 * dt)
            info["Nyquist Frequency (Hz)"] = f"{nyquist:.2f}"
            
            try:
                spec = np.abs(np.fft.rfft(traces[0]))
                freqs = np.fft.rfftfreq(len(traces[0]), dt)
                dom_freq_idx = np.argmax(spec[1:]) + 1
                dom_freq = freqs[dom_freq_idx]
                info["Dominant Frequency (Hz)"] = f"{dom_freq:.2f}"
            except:
                info["Dominant Frequency (Hz)"] = "N/A"
                
        except Exception as e:
            info["Signal Info Error"] = str(e)
        
        return info
    
    def _extract_trace_quality(self, segy):
        """Extract trace quality metrics"""
        info = {}
        try:
            n_traces = segy.tracecount
            sample_size = min(100, n_traces)
            step = max(1, n_traces // sample_size)
            
            traces = []
            for i in range(0, n_traces, step):
                if len(traces) >= sample_size:
                    break
                traces.append(segy.trace[i])
            traces = np.array(traces)
            
            # Null/Dead Traces
            zero_traces = np.sum(np.all(traces == 0, axis=1))
            estimated_null = int((zero_traces / len(traces)) * n_traces)
            info["Null/Dead Traces"] = f"{estimated_null}"
            info["Valid Traces"] = f"{n_traces - estimated_null}"
            
        except Exception as e:
            info["Trace Quality Error"] = str(e)
        
        return info
    
    def _extract_binary_header(self, segy):
        """Extract binary header information"""
        info = {}
        try:
            format_code = segy.format
            info["Binary Format Code"] = str(format_code)
            
            try:
                sorting_code = segy.bin[segyio.BinField.SortingCode]
                sorting_desc = self._get_sorting_description(sorting_code)
                info["Trace Sorting"] = sorting_desc
            except:
                info["Trace Sorting"] = "Not available"
            
            info["Endian Type"] = "Big Endian (SEG-Y standard)"
            
            try:
                meas_system = segy.bin[segyio.BinField.MeasurementSystem]
                meas_map = {1: "Meters", 2: "Feet"}
                info["Measurement System"] = meas_map.get(meas_system, f"Unknown ({meas_system})")
            except:
                info["Measurement System"] = "Not available"
                
        except Exception as e:
            info["Binary Header Error"] = str(e)
        
        return info
    
    def _extract_volume_stats(self, segy):
        """Extract volume statistics"""
        info = {}
        try:
            # Estimated Volume
            try:
                ilines = list(segy.ilines)
                xlines = list(segy.xlines)
                if ilines and xlines:
                    il_count = len(ilines)
                    xl_count = len(xlines)
                    info["Estimated Volume"] = f"{il_count} x {xl_count} traces"
                else:
                    info["Estimated Volume"] = "N/A"
            except:
                info["Estimated Volume"] = "N/A"
                
        except Exception as e:
            info["Volume Stats Error"] = str(e)
        
        return info
    
    # Original methods for table display and QC validation
    def validate_segy_file(self, segy):
        """Validate SEGY file against all QC criteria"""
        results = {}
        
        check_methods = {
            "format": self._format_check,
            "traces": self._trace_count_check,
            "samples": self._sample_count_check,
            "sample_interval": self._sample_interval_check,
            "trace_length": self._trace_length_check,
            "amplitude": self._amplitude_check,
            "null_traces": self._null_trace_check,
            "geometry": self._geometry_check,
            "inline_range": self._inline_check,
            "crossline_range": self._crossline_check
        }
        
        for key, check_method in check_methods.items():
            is_valid, reason = check_method(segy)
            results[key] = {
                "status": "Y" if is_valid else "N",
                "reason": reason
            }
        
        return results
    
    def get_basic_info(self, segy):
        """Get basic information for table display"""
        info = {}
        
        try:
            info["filename"] = os.path.basename(segy._filename) if hasattr(segy, '_filename') else "N/A"
            # info["survey_name"] = self._extract_survey_name(segy)
            info["trace_count"] = segy.tracecount
            info["sample_count"] = segy.samples.size
            
            interval = segy.bin[segyio.BinField.Interval] / 1000.0
            info["sample_interval"] = f"{interval:.2f}"
            
            trace_length = (segy.samples.size - 1) * interval
            info["trace_length"] = f"{trace_length:.0f}"
            
            format_code = segy.bin[segyio.BinField.Format]
            info["format"] = self._get_format_short(format_code)
            
            inline_range, xline_range = self._get_3d_ranges(segy)
            info["inline_range"] = inline_range
            info["crossline_range"] = xline_range
            
        except Exception as e:
            info["error"] = str(e)
        
        return info
    
    # QC CHECK METHODS
    def _format_check(self, segy):
        try:
            format_code = segy.bin[segyio.BinField.Format]
            valid_formats = [1, 2, 3, 5, 8]
            if format_code in valid_formats:
                return True, self._get_format_short(format_code)
            else:
                return False, f"Unknown: {format_code}"
        except:
            return False, "Error"
    
    def _trace_count_check(self, segy):
        try:
            trace_count = segy.tracecount
            if trace_count > 0:
                if trace_count > 10000:
                    return True, f"{trace_count:,}"
                else:
                    return False, f"{trace_count:,} (low for 3D)"
            else:
                return False, "0"
        except:
            return False, "Error"
    
    def _sample_count_check(self, segy):
        try:
            sample_count = segy.samples.size
            return (True, f"{sample_count}") if sample_count > 0 else (False, "0")
        except:
            return False, "Error"
    
    def _sample_interval_check(self, segy):
        try:
            interval = segy.bin[segyio.BinField.Interval]
            interval_ms = interval / 1000.0
            
            if 0.5 <= interval_ms <= 10:
                return True, f"{interval_ms:.2f} ms"
            else:
                return False, f"{interval_ms:.2f} ms"
        except:
            return False, "Error"
    
    def _trace_length_check(self, segy):
        try:
            dt = segy.bin[segyio.BinField.Interval] / 1000.0
            trace_length = (segy.samples.size - 1) * dt
            
            if 1000 <= trace_length <= 10000:
                return True, f"{trace_length:.0f} ms"
            else:
                return False, f"{trace_length:.0f} ms"
        except:
            return False, "Error"
    
    def _amplitude_check(self, segy):
        try:
            amp_stats = self._calculate_amplitude_stats(segy)
            
            if amp_stats['max'] == 0 and amp_stats['min'] == 0:
                return False, "All zeros"
            
            return True, f"{amp_stats['min']:.1f} to {amp_stats['max']:.1f}"
        except:
            return False, "Error"
    
    def _null_trace_check(self, segy):
        try:
            null_count = self._count_null_traces(segy)
            total_traces = segy.tracecount
            null_percent = (null_count / total_traces * 100) if total_traces > 0 else 0
            
            if null_percent < 5:
                return True, f"{null_count} ({null_percent:.1f}%)"
            else:
                return False, f"{null_count} ({null_percent:.1f}%)"
        except:
            return False, "Error"
    
    def _geometry_check(self, segy):
        try:
            sample_size = min(100, segy.tracecount)
            has_inline = False
            has_xline = False
            
            for i in range(sample_size):
                header = segy.header[i]
                il = header[segyio.TraceField.INLINE_3D]
                xl = header[segyio.TraceField.CROSSLINE_3D]
                
                if il != 0:
                    has_inline = True
                if xl != 0:
                    has_xline = True
                
                if has_inline and has_xline:
                    break
            
            if has_inline and has_xline:
                return True, "3D geometry detected"
            else:
                return False, "No 3D geometry info"
        except:
            return False, "Error"
    
    def _inline_check(self, segy):
        try:
            inline_range, _ = self._get_3d_ranges(segy)
            if inline_range != "N/A":
                return True, inline_range
            else:
                return False, "Not found"
        except:
            return False, "Error"
    
    def _crossline_check(self, segy):
        try:
            _, xline_range = self._get_3d_ranges(segy)
            if xline_range != "N/A":
                return True, xline_range
            else:
                return False, "Not found"
        except:
            return False, "Error"
    
    # HELPER METHODS
    @staticmethod
    def _extract_survey_name(segy):
        try:
            text_header = segyio.tools.wrap(segy.text[0])
            for line in text_header[:5]:
                if 'SURVEY' in line.upper() or '3D' in line.upper():
                    return line.strip()[:40]
            return "N/A"
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
            1: "IBM Float (32-bit)",
            2: "32-bit Integer",
            3: "16-bit Integer",
            5: "IEEE Float (32-bit)",
            8: "8-bit Integer"
        }
        return formats.get(format_code, f"Unknown (Code {format_code})")
    
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
    
    def _get_3d_ranges(self, segy):
        try:
            sample_size = min(1000, segy.tracecount)
            step = max(1, segy.tracecount // sample_size)
            
            inlines = []
            xlines = []
            
            for i in range(0, segy.tracecount, step):
                header = segy.header[i]
                il = header[segyio.TraceField.INLINE_3D]
                xl = header[segyio.TraceField.CROSSLINE_3D]
                
                if il != 0:
                    inlines.append(il)
                if xl != 0:
                    xlines.append(xl)
            
            if inlines:
                inline_range = f"{min(inlines)}-{max(inlines)}"
            else:
                inline_range = "N/A"
            
            if xlines:
                xline_range = f"{min(xlines)}-{max(xlines)}"
            else:
                xline_range = "N/A"
            
            return inline_range, xline_range
        except:
            return "N/A", "N/A"
    
    def _calculate_amplitude_stats(self, segy, sample_size=50):
        try:
            trace_count = min(sample_size, segy.tracecount)
            step = max(1, segy.tracecount // trace_count)
            
            all_samples = []
            for i in range(0, segy.tracecount, step):
                if len(all_samples) >= sample_size * 1000:
                    break
                trace = segy.trace[i]
                all_samples.extend(trace[::10])
            
            all_samples = np.array(all_samples)
            
            return {
                'min': float(np.min(all_samples)),
                'max': float(np.max(all_samples)),
                'mean': float(np.mean(all_samples)),
                'std': float(np.std(all_samples))
            }
        except:
            return {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
    
    def _count_null_traces(self, segy, sample_size=50):
        try:
            trace_count = min(sample_size, segy.tracecount)
            step = max(1, segy.tracecount // trace_count)
            
            null_count = 0
            sampled_count = 0
            
            for i in range(0, segy.tracecount, step):
                trace = segy.trace[i]
                if np.all(trace == 0) or np.all(np.isnan(trace)):
                    null_count += 1
                sampled_count += 1
            
            estimated_null = int((null_count / sampled_count) * segy.tracecount) if sampled_count > 0 else 0
            return estimated_null
        except:
            return 0