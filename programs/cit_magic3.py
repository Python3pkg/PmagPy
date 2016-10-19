#!/usr/bin/env python
#from builtins import range
import os,sys
import pmagpy.pmag as pmag
import pmagpy.new_builder as nb
from pandas import DataFrame
from pmagpy.mapping import map_magic as mapm


def main(command_line=True, **kwargs):
    """
    NAME
        cit_magic.py

    DESCRIPTION
        converts CIT and .sam  format files to magic_measurements format files

    SYNTAX
        cit_magic.py [command line options]

    OPTIONS
        -h: prints the help message and quits.
        -usr USER:   identify user, default is ""
        -f FILE: specify .sam format input file, required
        -fsi SITEFILE : specify file with site names and locations [tab delimited magic file]
        -F FILE: specify output  measurements file, default is magic_measurements.txt
        -Fsp FILE: specify output er_specimens.txt file, default is er_specimens.txt
        -Fsi FILE: specify output er_sites.txt file, default is er_sites.txt
        -Fsa FILE: specify output er_samples.txt file, default is er_samples.txt  # LORI
        -n [gm,kg,cc,m3]: specify normalization
        -A: don't average replicate measurements
        -spc NUM : specify number of characters to designate a  specimen, default = 0
        -ncn NCON: specify naming convention
        -loc LOCNAME : specify location/study name, must have either LOCNAME or SITEFILE or be a synthetic
        -mcd [FS-FD:SO-MAG,.....] colon delimited list for method codes applied to all specimens in .sam file
        -dc B PHI THETA: dc lab field (in micro tesla) and phi,theta, default is none
              NB: use PHI, THETA = -1 -1 to signal that it changes, i.e. in anisotropy experiment
        -ac B : peak AF field (in mT) for ARM acquisition, default is none
        -dm: specify which magic data model you want your output in 3.0 or 2.5 default is 3.0

    INPUT
        Best to put separate experiments (all AF, thermal, thellier, trm aquisition, Shaw, etc.)

    NOTES:
         Sample naming convention:
        [1] XXXXY: where XXXX is an arbitrary length site designation and Y
            is the single character sample designation.  e.g., TG001a is the
            first sample from site TG001.    [default]
        [2] XXXX-YY: YY sample from site XXXX (XXX, YY of arbitary length)
        [3] XXXX.YY: YY sample from site XXXX (XXX, YY of arbitary length)
        [4-Z] XXXX[YYY]:  YYY is sample designation with Z characters from site XXX
        [5] site name = sample name
        [6] site name entered in site_name column in the orient.txt format input file  -- NOT CURRENTLY SUPPORTED
        [7-Z] [XXX]YYY:  XXX is site designation with Z characters from samples  XXXYYY
        NB: all others you will have to either customize your
            self or e-mail ltauxe@ucsd.edu for help.
    """
    #
    #initialize variables
    norm='cc'
    samp_con,Z='3',1
    meas_file='measurements.txt'
    spec_file='specimens.txt'
    samp_file='samples.txt'
    site_file='sites.txt'
    loc_file='locations.txt'
    Specs,Samps,Sites,Locs=[],[],[],[]
    MeasRecs=[]
    specnum,units,locname=0,"1","unknown"
    citation="This study"
    dir_path='.'
    args=sys.argv
    if command_line:
        if '-WD' in args:
            ind=args.index("-WD")
            dir_path=args[ind+1]
        if "-h" in args:
            print(main.__doc__)
            return False
        if "-usr" in args:
            ind=args.index("-usr")
            user=args[ind+1]
        if '-F' in args:
            ind=args.index("-F")
            meas_file=args[ind+1]
        if '-Fsp' in args:
            ind=args.index("-Fsp")
            spec_file=args[ind+1]
        if '-Fsa' in args:
            ind=args.index("-Fsa")
            samp_file=args[ind+1]
        if '-Fsi' in args:   # LORI addition
            ind=args.index("-Fsi")
            site_file=args[ind+1]
        if '-loc' in args:
            ind=args.index("-loc")
            locname=args[ind+1]
        if '-mcd' in args:
            ind=args.index("-mcd")
            methods=args[ind+1]
        else:
            methods='SO-MAG'
        if '-spc' in args:
            ind=args.index("-spc")
            specnum=-int(args[ind+1])
        if '-n' in args:
            ind=args.index("-n")
            norm=args[ind+1]
        if "-A" in args:
            avg=1
        else:
            avg=0
        if "-ncn" in args:
            ind=args.index("-ncn")
            samp_con=sys.argv[ind+1]
            if "4" in samp_con:
                if "-" not in samp_con:
                    print("option [4] must be in form 4-Z where Z is an integer")
                    return False, "naming convention option [4] must be in form 4-Z where Z is an integer"
                else:
                    Z=samp_con.split("-")[1]
                    samp_con="4"
        if '-f' in args:
            ind=args.index("-f")
            magfile=args[ind+1]
        if '-ID' in args:
            ind = args.index('-ID')
            input_dir_path = args[ind+1]
        else:
            input_dir_path = dir_path
        output_dir_path = dir_path
        if '-dm' in args:
            dmi = args.index('-dm')
            data_model = args[dmi+1]

    # if you are running as a module:
    elif not command_line:
        dir_path = kwargs.get('dir_path', '.')
        user = kwargs.get('user', '')
        meas_file = kwargs.get('meas_file', 'measurements.txt') # outfile
        spec_file = kwargs.get('spec_file', 'specimens.txt') # specimen outfile
        samp_file = kwargs.get('samp_file', 'samples.txt') # sample outfile
        site_file = kwargs.get('site_file', 'sites.txt') # site outfile
        loc_file = kwargs.get('loc_file', 'locations.txt') # location outfile
        data_model = kwargs.get('data_model', 3.0) # data_model to output as
        locname = kwargs.get('locname', 'unknown')
        methods = kwargs.get('methods', ['SO-MAG'])
        specnum = -int(kwargs.get('specnum', 0))
        norm = kwargs.get('norm', 'cc')
        avg = kwargs.get('avg', 0)  # 0 means do average, 1 means don't
        samp_con = kwargs.get('samp_con', '3')
        magfile = kwargs.get('magfile', '')
        input_dir_path = kwargs.get('input_dir_path', dir_path)
        output_dir_path = dir_path
    # done with module-specific stuff

    # formatting and checking variables
    if locname=='' or locname==None: locname = 'unknown'
    if "4" in samp_con:
        if "-" not in samp_con:
            print("option [4] must be in form 4-Z where Z is an integer")
            return False, "naming convention option [4] must be in form 4-Z where Z is an integer"
        else:
            Z=samp_con.split("-")[1]
            samp_con="4"

    magfile = os.path.join(input_dir_path, magfile)
    spec_file = os.path.join(output_dir_path, spec_file)
    samp_file = os.path.join(output_dir_path, samp_file)
    site_file = os.path.join(output_dir_path, site_file)
    meas_file= os.path.join(output_dir_path, meas_file)
    try:
        file_input=open(magfile,'r')
    except Exception as ex:
        print("bad sam file name: ", magfile)
        return False, "bad sam file name"
    File = file_input.readlines()
    if len(File) == 1: File = File[0].split('\r'); File = [x+"\r\n" for x in File]
    sids,ln,format=[],0,'CIT'
    formats=['CIT','2G','APP','JRA']
    if File[ln].strip()=='CIT': ln+=1
    LocRec={}
    LocRec["er_location_name"]=locname
    LocRec["er_citation_names"]=citation
    comment=File[ln]
    if comment=='CIT':
       format=comment
       ln+=1
    comment=File[ln]
    print(comment)
    ln+=1
    specimens,samples,sites=[],[],[]
    if format=='CIT':
        line=File[ln].split()
        site_lat=line[0]
        site_lon=line[1]
        LocRec["location_begin_lat"]=site_lat
        LocRec["location_begin_lon"]=site_lon
        LocRec["location_end_lat"]=site_lat
        LocRec["location_end_lon"]=site_lon
        Locs.append(LocRec)
        Cdec=float(line[2])
        for k in range(ln+1,len(File)):
            line=File[k]
            rec=line.split()
            if rec == []: continue
            specimen=rec[0]
            specimens.append(specimen)
    for specimen in specimens:
        SpecRec,SampRec,SiteRec={},{},{}
        if specnum!=0:
            sample=specimen[:specnum]
        else: sample=specimen
        site=pmag.parse_site(sample,samp_con,Z)
        SpecRec['er_specimen_name']=specimen
        SpecRec['er_sample_name']=sample
        SpecRec['er_site_name']=site
        SpecRec['er_location_name']=locname
        SpecRec['er_citation_names']=citation
        SampRec['er_sample_name']=sample
        SampRec['er_site_name']=site
        SampRec['er_location_name']=locname
        SampRec['er_citation_names']=citation
        SampRec['magic_method_codes']=methods
        SampRec['sample_declination_correction']='%7.1f'%(Cdec)
        SiteRec['er_site_name']=site
        SiteRec['er_location_name']=locname
        SiteRec['er_citation_names']=citation
        SiteRec['site_lat']=site_lat
        SiteRec['site_lon']=site_lon
        f=open(input_dir_path+'/'+specimen,'rU')
        Lines=f.readlines()
        comment=""
        line=Lines[0].split()
        if len(line)>2:
            comment=line[2]
        info=Lines[1].split()
        vol=float(info[-1])
        if vol!=1.0:
            if norm=='cc':units="1"
            if norm=='m3':units="2"
            SpecRec['specimen_weight']=""
            if units=="1" or "":
                SpecRec['specimen_volume']='%10.3e'%(vol*1e-6)
            else:
                SpecRec['specimen_volume']='%10.3e'%(vol)
        else:
            if norm=='cc':units="1"
            if norm=='m3':units="2"
            SpecRec['specimen_volume']=""
            if units=="1" or "":
                SpecRec['specimen_weight']='%10.3e'%(vol*1e-3)
            else:
                SpecRec['specimen_weight']='%10.3e'%(vol)
        dip=float(info[-2])
        dip_direction=float(info[-3])+Cdec+90.
        sample_dip=-float(info[-4])
        sample_azimuth=float(info[-5])+Cdec-90.
        if len(info)>5:
            SampRec['sample_height']=info[-6]
        else:
            SampRec['sample_height']='0'
        SampRec['sample_azimuth']='%7.1f'%(sample_azimuth)
        SampRec['sample_dip']='%7.1f'%(sample_dip)
        SampRec['sample_bed_dip']='%7.1f'%(dip)
        SampRec['sample_bed_dip_direction']='%7.1f'%(dip_direction)
        SampRec['sample_class']=''
        SampRec['sample_type']=''
        SampRec['sample_lithology']=''
        if Cdec!=0 or Cdec!="":
            SampRec['magic_method_codes']='SO-CMD-NORTH'
        else:
            SampRec['magic_method_codes']='SO-MAG'
        for line in Lines[2:len(Lines)]:
            #print 'line:', line
            MeasRec=SpecRec.copy()

#           Remove specimen_volume and specimen_weight as they do not exits in the magic_measurement table
            del MeasRec["specimen_volume"]
            del MeasRec["specimen_weight"]

            treat_type=line[0:3]
            treat=line[2:6]
            try: float(treat)
            except ValueError: treat = line[3:6]
            if treat_type.startswith('NRM'):
                MeasRec['magic_method_codes']='LT-NO'
                MeasRec['measurement_temp']='273'
                MeasRec['treatment_temp']='273'
                MeasRec['treatment_dc_field']='0'
                MeasRec['treatment_ac_field']='0'
            elif treat_type.startswith('AF'):
                MeasRec['magic_method_codes']='LT-AF-Z'
                MeasRec['measurement_temp']='273'
                MeasRec['treatment_temp']='273'
                MeasRec['treatment_dc_field']='0'
                if treat.strip() == '':
                    MeasRec['treatment_ac_field']='0'
                else:
                    MeasRec['treatment_ac_field']='%10.3e'%(float(treat)*1e-3)
            elif treat_type.startswith('ARM'):
                MeasRec['magic_method_codes']="LP-ARM"
                MeasRec['measurement_temp']='273'
                MeasRec['treatment_temp']='273'
                MeasRec['treatment_dc_field']='0'
                if treat.strip() == '':
                    MeasRec['treatment_ac_field']='0'
                else:
                    MeasRec['magic_method_codes']="LP-ARM-AFD"
                    MeasRec['treatment_ac_field']='%10.3e'%(float(treat)*1e-3)
            elif treat_type.startswith('TT'):
                MeasRec['magic_method_codes']='LT-T-Z'
                MeasRec['measurement_temp']='273'
                if treat.strip() == '':
                    MeasRec['treatment_temp']='273'
                else:
                    MeasRec['treatment_temp']='%7.1f'%(float(treat)+273)
                MeasRec['treatment_dc_field']='0'
                MeasRec['treatment_ac_field']='0'
            elif treat_type.startswith('LT') or treat_type.startswith('LN2'):
                MeasRec['magic_method_codes']='LT-LT-Z'
                MeasRec['measurement_temp']='273'
                MeasRec['treatment_temp']='77'
                MeasRec['treatment_dc_field']='0'
                MeasRec['treatment_ac_field']='0'
            else:
                print("trouble with your treatment steps")
            MeasRec['measurement_dec']=line[46:51]
            MeasRec['measurement_inc']=line[52:58]
            M='%8.2e'%(float(line[31:39])*vol*1e-3) # convert to Am2
            MeasRec['measurement_magn_moment']=M
            MeasRec['measurement_csd']='%7.1f'%(eval(line[41:46]))
            MeasRec["measurement_positions"]='1'
            MeasRec['measurement_standard']='u'
            if len(line)>60:
                MeasRec['magic_instrument_codes']=line[85:].strip('\n \r \t "')
                MeasRec['measurement_sd_x']='%8.2e'%(float(line[58:67])*1e-8) #(convert e-5emu to Am2)
                MeasRec['measurement_sd_y']='%8.2e'%(float(line[67:76])*1e-8)
                MeasRec['measurement_sd_z']='%8.2e'%(float(line[76:85])*1e-8)
            MeasRecs.append(MeasRec)
        Specs.append(SpecRec)
        if sample not in samples:
            samples.append(sample)
            Samps.append(SampRec)
        site=pmag.parse_site(sample,samp_con,Z)
        if site not in sites:
            sites.append(site)
            Sites.append(SiteRec)

    if float(data_model)==3.0:
        con = nb.Contribution('.',read_tables=[])

        con.add_empty_magic_table('specimens')
        con.add_empty_magic_table('samples')
        con.add_empty_magic_table('sites')
        con.add_empty_magic_table('locations')
        con.add_empty_magic_table('measurements')

        con.tables['specimens'].df = DataFrame(Specs).rename(columns=mapm.spec_magic2_2_magic3_map)
        con.tables['samples'].df = DataFrame(Samps).rename(columns=mapm.samp_magic2_2_magic3_map)
        con.tables['sites'].df = DataFrame(Sites).rename(columns=mapm.site_magic2_2_magic3_map)
        con.tables['locations'].df = DataFrame(Locs).rename(columns=mapm.loc_magic2_2_magic3_map)
        Fixed=pmag.measurements_methods(MeasRecs,avg)
        con.tables['measurements'].df = DataFrame(Fixed).rename(columns=mapm.meas_magic2_2_magic3_map)

        con.tables['specimens'].write_magic_file(custom_name=spec_file)
        print('specimens stored in ',spec_file)
        con.tables['samples'].write_magic_file(custom_name=samp_file)
        print('samples stored in ',samp_file)
        con.tables['sites'].write_magic_file(custom_name=site_file)
        print('sites stored in ', site_file)
        con.tables['locations'].write_magic_file(custom_name=loc_file)
        print('locations stored in ', loc_file)
        con.tables['measurements'].write_magic_file(custom_name=meas_file)
        print('data stored in ',meas_file)
    else:
        pmag.magic_write(spec_file,Specs,'er_specimens')
        print('specimens stored in ',spec_file)
        pmag.magic_write(samp_file,Samps,'er_samples')
        print('samples stored in ',samp_file)
        pmag.magic_write(site_file,Sites,'er_sites')
        print('sites stored in ', site_file)
        Fixed=pmag.measurements_methods(MeasRecs,avg)
        pmag.magic_write(meas_file,Fixed,'magic_measurements')
        print('data stored in ',meas_file)
        return True, meas_file

    return True, meas_file

def do_help():
    return main.__doc__

if __name__ == "__main__":
    main()
