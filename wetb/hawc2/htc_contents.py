'''
Created on 20/01/2014

@author: MMPE

See documentation of HTCFile below

'''
from collections import OrderedDict
import collections


class OrderedDict(collections.OrderedDict):
    pass

    def __str__(self):
        return "\n".join(["%-30s\t %s" % ((str(k) + ":"), str(v)) for k, v in self.items()])


def parse_next_line(lines):
    line, *comments = lines.pop(0).split(";")
    comments = ";".join(comments).rstrip()
    while lines and lines[0].lstrip().startswith(";"):
        comments += "\n%s" % lines.pop(0).rstrip()
    return line.strip(), comments

class HTCContents(object):
    lines = []
    contents = None
    name_ = ""

    def __setitem__(self, key, value):
        self.contents[key] = value

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.replace(".", "/")
            if "/" in key:
                keys = key.split('/')
                val = self.contents[keys[0]]
                for k in keys[1:]:
                    val = val[k]
                return val
            return self.contents[key]
        else:
            return self.values[key]

    def __getattribute__(self, *args, **kwargs):
        try:
            return object.__getattribute__(self, *args, **kwargs)
        except:
            return self.contents[args[0]]

    def __setattr__(self, *args, **kwargs):
        k, *v = args
        if k in dir(self):  # in ['section', 'filename', 'lines']:
            return object.__setattr__(self, *args, **kwargs)
        self.contents[k] = HTCLine(k, v, "")

    def __delattr__(self, *args, **kwargs):
        k, = args
        if k in self:
            del self.contents[k]

    def __iter__(self):
        return iter(self.contents.values())


    def __contains__(self, key):
        return key in self.contents

    def get(self, section, default=None):
        try:
            return self[section]
        except KeyError:
            return default

    def keys(self):
        return list(self.contents.keys())

    def _add_contents(self, contents):
        if contents.name_ not in self:
            self[contents.name_] = contents
        else:
            ending = "__2"
            while contents.name_ + ending in self:
                ending = "__%d" % (1 + float("0%s" % ending.replace("__", "")))
            self[contents.name_ + ending] = contents

    def add_section(self, name, allow_duplicate_section=False):
        if name in self and allow_duplicate_section is False:
            return self[name]
        section = HTCSection(name)
        self._add_contents(section)
        return section

    def add_line(self, name, values, comments):
        self._add_contents(HTCLine(name, values, comments))




class HTCSection(HTCContents):
    end_comments = ""
    begin_comments = ""
    def __init__(self, name, begin_comments="", end_comments=""):
        self.name_ = name
        self.begin_comments = begin_comments
        self.end_comments = end_comments
        self.contents = OrderedDict()

    @staticmethod
    def from_lines(lines):
        line, begin_comments = parse_next_line(lines)
        name = line[6:].lower()
        if name == "output":
            section = HTCOutputSection(name, begin_comments)
        elif name.startswith("output_at_time"):
            section = HTCOutputAtTimeSection(name, begin_comments)
        else:
            section = HTCSection(name, begin_comments)
        while lines:
            if lines[0].lower().startswith("begin"):
                section._add_contents(HTCSection.from_lines(lines))
            elif lines[0].lower().startswith("end"):
                line, section.end_comments = parse_next_line(lines)
                break
            else:
                section._add_contents(section.line_from_line(lines))
        return section

    def line_from_line(self, lines):
        return HTCLine.from_lines(lines)

    def __str__(self, level=0):
        s = "%sbegin %s;%s\n" % ("  "*level, self.name_, ("", "\t" + self.begin_comments)[bool(self.begin_comments.strip())])
        s += "".join([c.__str__(level + 1) for c in self])
        s += "%send %s;%s\n" % ("  "*level, self.name_, ("", "\t" + self.end_comments)[self.end_comments.strip() != ""])
        return s

class HTCLine(HTCContents):
    values = None
    comments = ""
    def __init__(self, name, values, comments):
        self.name_ = name
        self.values = values
        self.comments = comments

    def __repr__(self):
        return str(self)

    def __str__(self, level=0):
        return "%s%s%s;%s\n" % ("  "*(level), self.name_,
                                  ("", "\t" + self.str_values())[bool(self.values)],
                                  ("", "\t" + self.comments)[bool(self.comments.strip())])
    def str_values(self):
        return " ".join([str(v) for v in self.values])

    def __getitem__(self, key):
        return self.values[key]

    @staticmethod
    def from_lines(lines):
        line, end_comments = parse_next_line(lines)
        if len(line.split()) > 0:
            name, *values = line.split()
        else:
            name = line
            values = []
        def fmt(v):
            try:
                if int(float(v)) == float(v):
                    return int(float(v))
                return float(v)
            except ValueError:
                return v
        values = [fmt(v) for v in values]
        return HTCLine(name, values, end_comments)


class HTCOutputSection(HTCSection):
    sensors = None
    def __init__(self, name, begin_comments="", end_comments=""):
        HTCSection.__init__(self, name, begin_comments=begin_comments, end_comments=end_comments)
        self.sensors = []

    def add_sensor(self, type, sensor, values=[], comment="", nr=None):
        self._add_sensor(HTCSensor(type, sensor, values, comment), nr)


    def _add_sensor(self, htcSensor, nr=None):
        if nr is None:
            nr = len(self.sensors)
        self.sensors.insert(nr, htcSensor)


    def line_from_line(self, lines):
        name = lines[0].split()[0].strip()
        if name in ['filename', 'data_format', 'buffer', 'time']:
            return HTCLine.from_lines(lines)
        else:
            return HTCSensor.from_lines(lines)

    def _add_contents(self, contents):
        if isinstance(contents, HTCSensor):
            self._add_sensor(contents)
        else:
            return HTCSection._add_contents(self, contents)


    def __str__(self, level=0):
        s = "%sbegin %s;%s\n" % ("  "*level, self.name_, ("", "\t" + self.begin_comments)[len(self.begin_comments.strip())])
        s += "".join([c.__str__(level + 1) for c in self])
        s += "".join([s.__str__(level + 1) for s in self.sensors])
        s += "%send %s;%s\n" % ("  "*level, self.name_, ("", "\t" + self.end_comments)[self.end_comments.strip() != ""])
        return s

class HTCOutputAtTimeSection(HTCOutputSection):
    type = None
    time = None
    def __init__(self, name, begin_comments="", end_comments=""):
        name, self.type, time = name.split()
        self.time = float(time)
        HTCOutputSection.__init__(self, name, begin_comments=begin_comments, end_comments=end_comments)

    def __str__(self, level=0):
        s = "%sbegin %s %s %s;%s\n" % ("  "*level, self.name_, self.type, self.time, ("", "\t" + self.begin_comments)[len(self.begin_comments.strip())])
        s += "".join([c.__str__(level + 1) for c in self])
        s += "".join([s.__str__(level + 1) for s in self.sensors])
        s += "%send %s;%s\n" % ("  "*level, self.name_, ("", "\t" + self.end_comments)[self.end_comments.strip() != ""])
        return s

class HTCSensor(HTCLine):
    type = ""
    sensor = ""
    values = []

    def __init__(self, type, sensor, values, comments):
        self.type = type
        self.sensor = sensor
        self.values = values
        self.comments = comments

    @staticmethod
    def from_lines(lines):
        line, comments = parse_next_line(lines)
        if len(line.split()) > 2:
            type, sensor, *values = line.split()
        else:
            type, sensor = line.split()
            values = []
        def fmt(v):
            try:
                if int(float(v)) == float(v):
                    return int(float(v))
                return float(v)
            except ValueError:
                return v
        values = [fmt(v) for v in values]
        return HTCSensor(type, sensor, values, comments)

    def __str__(self, level=0):
        return "%s%s %s%s;%s\n" % ("  "*(level),
                                self.type,
                                self.sensor,
                                ("", "\t" + self.str_values())[bool(self.values)],
                                ("", "\t" + self.comments)[bool(self.comments.strip())])

class HTCDefaults(object):


    empty_htc = """begin simulation;
        time_stop 600;
        solvertype    1;    (newmark)
        on_no_convergence continue;
        convergence_limits 1E3 1.0 1E-7; ; . to run again, changed 07/11
        begin newmark;
          deltat    0.02;
        end newmark;
    end simulation;
    ;
    ;----------------------------------------------------------------------------------------------------------------------------------------------------------------
    ;
    begin new_htc_structure;
      begin orientation;
      end orientation;
      begin constraint;
      end constraint;
    end new_htc_structure;
    ;
    ;----------------------------------------------------------------------------------------------------------------------------------------------------------------
    ;
    begin wind ;
      density                 1.225 ;
      wsp                     10   ;
      tint                    1;
      horizontal_input        1     ;            0=false, 1=true
      windfield_rotations     0 0.0 0.0 ;    yaw, tilt, rotation
      center_pos0             0 0 -30 ; hub heigth
      shear_format            1   0;0=none,1=constant,2=log,3=power,4=linear
      turb_format             0     ;  0=none, 1=mann,2=flex
      tower_shadow_method     0     ;  0=none, 1=potential flow, 2=jet
    end wind;
    ;
    ;----------------------------------------------------------------------------------------------------------------------------------------------------------------
    ;
    begin dll;
    end dll;
    ;
    ;----------------------------------------------------------------------------------------------------------------------------------------------------------------
    ;
    begin output;
      general time;
    end output;
    exit;"""


    def add_mann_turbulence(self, L=29.4, ae23=1, Gamma=3.9, seed=1001, high_frq_compensation=True,
                            filenames=None,
                            no_grid_points=(4096, 32, 32), box_dimension=(6000, 100, 100),
                            std_scaling=(1, .8, .5)):
        wind = self.add_section('wind')
        wind.turb_format = (1, "0=none, 1=mann,2=flex")
        mann = wind.add_section('mann')
        mann.add_line('create_turb_parameters', [L, ae23, Gamma, seed, int(high_frq_compensation)], "L, alfaeps, gamma, seed, highfrq compensation")
        if filenames is None:
            filenames = ["./turb/turb_wsp%d_s%04d%s.bin" % (self.wind.wsp[0], seed, c) for c in ['u', 'v', 'w']]
        if isinstance(filenames, str):
            filenames = ["./turb/%s_s%04d%s.bin" % (filenames, seed, c) for c in ['u', 'v', 'w']]
        for filename, c in zip(filenames, ['u', 'v', 'w']):
            setattr(mann, 'filename_%s' % c, filename)
        for c, n, dim in zip(['u', 'v', 'w'], no_grid_points, box_dimension):
            setattr(mann, 'box_dim_%s' % c, "%d %.4f" % (n, dim / (n - 1)))
        if std_scaling is None:
            mann.dont_scale = 1
        else:
            try:
                del mann.dont_scale
            except KeyError:
                pass
            mann.std_scaling = "%f %f %f" % std_scaling