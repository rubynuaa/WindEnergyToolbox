'''
Created on 01/10/2014

@author: MMPE
'''
import xlrd
import pandas as pd
import numpy as np
import glob
import os
import functools

from wetb.hawc2.sel_file import SelFile
from wetb.functions.caching import cache_function
from collections import OrderedDict
HOURS_PR_20YEAR = 20 * 365 * 24

def Weibull(u, k, start, stop, step):
    C = 2 * u / np.sqrt(np.pi)
    cdf = lambda x :-np.exp(-(x / C) ** k)

    return {wsp:-cdf(wsp - step / 2) + cdf(wsp + step / 2) for wsp in np.arange(start, stop + step, step)}

def Weibull2(u, k, wsp_lst):
    C = 2 * u / np.sqrt(np.pi)
    cdf = lambda x :-np.exp(-(x / C) ** k)
    edges = np.r_[wsp_lst[0] - (wsp_lst[1] - wsp_lst[0]) / 2, (wsp_lst[1:] + wsp_lst[:-1]) / 2, wsp_lst[-1] + (wsp_lst[-1] - wsp_lst[-2]) / 2]
    return [-cdf(e1) + cdf(e2) for wsp, e1, e2 in zip(wsp_lst, edges[:-1], edges[1:])]


class DLCHighLevel(object):
    def __init__(self, filename, fail_on_resfile_not_found=False):
        self.filename = filename
        self.fail_on_resfile_not_found = fail_on_resfile_not_found
        wb = xlrd.open_workbook(self.filename)

        # Variables
        sheet = wb.sheet_by_name("Variables")
        for row_index in range(1, sheet.nrows):
            name = str(sheet.cell(row_index, 0).value).lower()
            value = sheet.cell(row_index, 1).value
            setattr(self, name, value)
        if not hasattr(self, "res_path"):
            raise Warning("The 'Variables' sheet of '%s' must contain the variable 'res_path' specifying the path to the result folder" % self.filename)
        self.res_path = os.path.join(os.path.dirname(self.filename), self.res_path)

        #DLC sheet
        sheet = wb.sheet_by_name("DLC")
        self.dlc_df = pd.DataFrame({sheet.cell(0, col_index).value.lower(): [sheet.cell(row_index, col_index).value for row_index in range(2, sheet.nrows) if sheet.cell(row_index, 0).value != ""] for col_index in range(sheet.ncols)})
        for k in ['load', 'dlc_dist', 'wsp_dist']:
            assert k.lower() in self.dlc_df.keys(), "DLC sheet must have a '%s' column" % k
        self.dist_value_keys = [('dlc_dist', 'dlc'), ('wsp_dist', 'wsp')]
        self.dist_value_keys.extend([(k, k.replace("_dist", "")) for k in self.dlc_df.keys() if k.endswith("_dist") and k not in ('dlc_dist', 'wsp_dist')])
        for i, (dk, vk) in enumerate(self.dist_value_keys):
            try:
                assert vk in self.dlc_df.keys(), "DLC sheet must have a '%s'-column when having a '%s'-column" % (vk, dk)
            except AssertionError as e:
                if vk == "dlc" and 'name' in self.dlc_df.keys():
                    columns = list(self.dlc_df.columns)
                    columns[columns.index('name')] = 'dlc'
                    self.dlc_df.columns = columns
                else:
                    raise e
            self.dlc_df[vk] = [str(n).lower().replace(vk, "") for n in self.dlc_df[vk]]
        if 'psf' not in self.dlc_df:
            self.dlc_df['psf'] = 1

        # Sensors sheet
        sheet = wb.sheet_by_name("Sensors")
        name_col_index = [sheet.cell(0, col_index).value.lower() for col_index in range(0, sheet.ncols)].index("name")
        self.sensor_df = pd.DataFrame({sheet.cell(0, col_index).value.lower(): [sheet.cell(row_index, col_index).value for row_index in range(1, sheet.nrows) if sheet.cell(row_index, name_col_index).value != ""] for col_index in range(sheet.ncols)})
        for k in ['Name', 'Nr']:
            assert k.lower() in self.sensor_df.keys(), "Sensor sheet must have a '%s' column" % k
        assert not any(self.sensor_df['name'].duplicated()), "Duplicate sensor names: %s" % ",".join(self.sensor_df['name'][self.sensor_df['name'].duplicated()].values)
        for k in ['description', 'unit', 'statistic', 'ultimate', 'fatigue', 'm', 'neql', 'extremeload', 'bearingdamage', 'mindistance', 'maxdistance']:
            if k not in self.sensor_df.keys():
                self.sensor_df[k] = ""
        for _, row in self.sensor_df[self.sensor_df['fatigue'] != ""].iterrows():
            assert isinstance(row['m'], (int, float)), "Invalid m-value for %s (m='%s')" % (row['name'], row['m'])
            assert isinstance(row['neql'], (int, float)), "Invalid NeqL-value for %s (NeqL='%s')" % (row['name'], row['neql'])
        for name, nrs in zip(self.sensor_info("extremeload").name, self.sensor_info("extremeload").nr):
            assert (np.atleast_1d((eval(str(nrs)))).shape[0] == 6), "'Nr' for Extremeload-sensor '%s' must contain 6 sensors (Fx,Fy,Fz,Mx,My,Mz)" % name


    def __str__(self):
        return self.filename


    def sensor_info(self, sensors=[]):
        if sensors != []:
            return self.sensor_df[functools.reduce(np.logical_or, [((self.sensor_df.get(f, np.array([""] * len(self.sensor_df.name))).values != "") | (self.sensor_df.name == f)) for f in np.atleast_1d(sensors)])]
        else:
            return self.sensor_df

    def dlc_variables(self, dlc):
        dlc_row = self.dlc_df[self.dlc_df['name'] == dlc]
        def get_lst(x):
            if isinstance(x, pd.Series):
                x = x.iloc[0]
            if ":" in str(x):
                start, step, stop = [float(eval(v, globals(), self.__dict__)) for v in x.lower().split(":")]
                return list(np.arange(start, stop + step, step))
            else:
                return [float(eval(v, globals(), self.__dict__)) for v in str(x).lower().replace("/", ",").split(",")]
        wsp = get_lst(dlc_row['wsp'])
        wdir = get_lst(dlc_row['wdir'])
        return wsp, wdir

    def distribution(self, value_key, dist_key, row):
        values = self.dlc_df[value_key][row]
        if ":" in values:
            start, step, stop = [float(eval(v, globals(), self.__dict__)) for v in values.lower().split(":")]
            values = np.arange(start, stop + step, step)
        else:
            values = [(eval(v, globals(), self.__dict__)) for v in str(values).lower().replace("/", ",").split(",")]

        dist = self.dlc_df[dist_key][row]
        if str(dist).lower() == "weibull" or str(dist).lower() == "rayleigh":
            dist = Weibull2(self.vref * .2, 2, values)
        else:
            def fmt(v):
                if "#" in str(v):
                    return v
                else:
                    if v == "":
                        return 0
                    else:
                        return float(v) / 100
            dist = [fmt(v) for v in str(self.dlc_df[dist_key][row]).replace("/", ",").split(",")]
        assert len(values) == len(dist), "Number of %s-values (%d)!= number of %s-values(%d)" % (value_key, len(values), dist_key, len(dist))
        return OrderedDict(zip(map(self.format_tag_value, values), dist))

    def fatigue_distribution(self):
        fatigue_dist = {}
        for row, load in enumerate(self.dlc_df['load']):
            if "F" not in str(load).upper():
                continue
            dlc = self.dlc_df[self.dist_value_keys[0][1]][row]
            fatigue_dist[str(dlc)] = [self.distribution(value_key, dist_key, row) for dist_key, value_key in self.dist_value_keys]
        return fatigue_dist



    def files_dict(self):
        if not hasattr(self, "res_folder") or self.res_folder == "":
            files = glob.glob(os.path.join(self.res_path, "*.sel")) + glob.glob(os.path.join(self.res_path, "*/*.sel"))
        else:
            files = []
            fatigue_dlcs = self.dlc_df[['F' in str(l).upper() for l in self.dlc_df['load']]]['dlc']
            for dlc_id in fatigue_dlcs:
                dlc_id = str(dlc_id)
                if "%" in self.res_folder:
                    folder = self.res_folder % dlc_id
                else:
                    folder = self.res_folder
                files.extend(glob.glob(os.path.join(self.res_path , folder, "*.sel")))
        keys = list(zip(*self.dist_value_keys))[1]
        fmt = self.format_tag_value
        tags = [[fmt(tag.replace(key, "")) for tag, key in zip(os.path.basename(f).split("_"), keys)] for f in files]
        dlc_tags = list(zip(*tags))[0]
        files_dict = {dlc_tag:{} for dlc_tag in dlc_tags}
        for tag_row, f in zip(tags, files):
            d = files_dict[tag_row[0]]
            for tag in tag_row[1:]:
                if tag not in d:
                    d[tag] = {}
                d = d[tag]
            if 'files' not in d:
                d['files'] = []
            d['files'].append(f)
        return files_dict

    def format_tag_value(self, v):
        try:
            if int(float(v)) == float(v):
                return int(float(v))
            return float(v)
        except ValueError:
            return v

    def probability(self, props, f, files):
        total_prop = 1
        for prop in props[::-1]:
            if str(prop).startswith("#"):
                duration = SelFile(f).duration
                prop = float(prop[1:]) * duration / (60 * 60 * 24 * 365)
                return prop * total_prop
            else:
                total_prop *= prop
        return total_prop


    def file_hour_lst(self):
        """Create a list of (filename, hours_pr_year) that can be used as input for LifeTimeEqLoad

        Returns
        -------
        file_hour_lst : list
            [(filename, hours),...] where\n
            - filename is the name of the file, including path
            - hours is the number of hours pr. 20 year of this file
        """

        fh_lst = []
        dist_dict = self.fatigue_distribution()
        files_dict = self.files_dict()



        for dlc_id in sorted(dist_dict.keys()):
            dlc_id = str(dlc_id)

            fmt = self.format_tag_value
            def tag_prop_lst(dist_lst):
                if len(dist_lst) == 0:
                    return [[]]
                return [[(fmt(tag), prop)] + tl for tl in tag_prop_lst(dist_lst[1:]) for tag, prop in dist_lst[0].items()]

            def files_from_tags(self, f_dict, tags):
                if len(tags) == 0:
                    return f_dict['files']
                try:
                    return files_from_tags(self, f_dict[tags[0]], tags[1:])
                except KeyError:
                    if self.dist_value_keys[-len(tags)][1] == "wdir":
                        try:
                            return files_from_tags(self, f_dict[tags[0] % 360], tags[1:])
                        except:
                            pass
                    raise

            for tag_props in (tag_prop_lst(dist_dict[dlc_id])):
                tags, props = zip(*tag_props)
                try:
                    files = (files_from_tags(self, files_dict, tags))
                except KeyError:
                    if self.fail_on_resfile_not_found:
                        raise FileNotFoundError("Result files for %s not found" % (", ".join(["%s='%s'" % (dv[1], t) for dv, t in zip(self.dist_value_keys, tags)])))
                    else:
                        continue
                if files:
                    f_prob = self.probability(props, files[0], files) / len(files)
                    f_hours_pr_20year = HOURS_PR_20YEAR * f_prob
                    for f in files:
                        fh_lst.append((f, f_hours_pr_20year))
        return fh_lst



    def dlc_lst(self, load='all'):
        dlc_lst = np.array(self.dlc_df['dlc'])[np.array([load == 'all' or load.lower() in d.lower() for d in self.dlc_df['load']])]
        return [v.lower().replace('dlc', '') for v in dlc_lst]

    @cache_function
    def psf(self):
        return {dlc: float((psf, 1)[psf == ""]) for dlc, psf in zip(self.dlc_df['dlc'], self.dlc_df['psf']) if dlc != ""}

if __name__ == "__main__":
    dlc_hl = DLCHighLevel(r'X:\NREL5MW\dlc.xlsx')
    #print (DLCHighLevelInputFile(r'C:\mmpe\Projects\DLC.xlsx').sensor_info(0, 0, 1)['Name'])
    #print (dlc_dict()['64'])
    #print (dlc_hl.fatigue_distribution()['64'])
    print (dlc_hl.file_hour_lst(r"X:\NREL5MW/C0008/res/"))

