#pylint: skip-file
#pylint: disable-all
# causes too many errors and crashes

import numpy,string,sys
from numpy import random
import numpy.linalg
import exceptions
import os
import time
#import check_updates
import scipy
from scipy import array,sqrt,mean

#pylint: skip-file

#check_updates.main() # check for updates

def get_version():
    import check_updates
    version=check_updates.get_version()
    return version


def sort_diclist(undecorated,sort_on):
    decorated=[(dict_[sort_on],dict_) for dict_ in undecorated]
    decorated.sort()
    return[dict_ for (key, dict_) in decorated]


def get_dictitem(In,k,v,flag):
    """ returns a list of dictionaries from list In with key,k  = value, v . CASE INSENSITIVE # allowed keywords:"""
    try:
        if flag=="T":return [dictionary for dictionary in In if dictionary[k].lower()==v.lower()] # return that which is
        if flag=="F":
            return [dictionary for dictionary in In if dictionary[k].lower()!=v.lower()] # return that which is not
        if flag=="has":return [dictionary for dictionary in In if v.lower() in dictionary[k].lower()] # return that which is contained
        if flag=="not":return [dictionary for dictionary in In if v.lower() not in dictionary[k].lower()] # return that which is not contained
        if flag=="eval":
            A=[dictionary for dictionary in In if dictionary[k]!=''] # find records with no blank values for key
            return [dictionary for dictionary in A if float(dictionary[k])==float(v)] # return that which is
        if flag=="min":
            A=[dictionary for dictionary in In if dictionary[k]!=''] # find records with no blank values for key
            return [dictionary for dictionary in A if float(dictionary[k])>=float(v)] # return that which is greater than
        if flag=="max":
            A=[dictionary for dictionary in In if dictionary[k]!=''] # find records with no blank values for key
            return [dictionary for dictionary in A if float(dictionary[k])<=float(v)] # return that which is less than
    except Exception, err:
        return []

def get_dictkey(In,k,dtype):
    """
        returns list of given key (k)  from input list of dictionaries (In) in data type dtype.  uses command:
        get_dictkey(In,k,dtype).  If dtype =="", data are strings; if "int", data are integers; if "f", data are floats.
    """

    Out=[]
    for d in In:
        if dtype=='': Out.append(d[k])
        if dtype=='f':
            if d[k]=="":
                Out.append(0)
            else:
                Out.append(float(d[k]))
        if dtype=='int':
            if d[k]=="":
                Out.append(0)
            else:
                Out.append(int(d[k]))
    return Out

def find(f,seq):
    for item in seq:
       if f in item: return item
    return ""

def get_orient(samp_data,er_sample_name):
    # set orientation priorities
    EX=["SO-ASC","SO-POM"]
    orient={'er_sample_name':er_sample_name,'sample_azimuth':"",'sample_dip':"",'sample_description':""}
    orients=get_dictitem(samp_data,'er_sample_name',er_sample_name,'T') # get all the orientation data for this sample
    if 'sample_orientation_flag' in orients[0].keys(): orients=get_dictitem(orients,'sample_orientation_flag','b','F') # exclude all samples with bad orientation flag
    if len(orients)>0:orient=orients[0] # re-initialize to first one
    methods=get_dictitem(orients,'magic_method_codes','SO-','has')
    methods=get_dictkey(methods,'magic_method_codes','') # get a list of all orientation methods for this sample
    SO_methods=[]
    for methcode in methods:
        meths=methcode.split(":")
        for meth in meths:
           if meth.strip() not in EX:SO_methods.append(meth)
   # find top priority orientation method
    if len(SO_methods)==0:
        print "no orientation data for ",er_sample_name
        az_type="SO-NO"
    else:
        SO_priorities=set_priorities(SO_methods,0)
        az_type=SO_methods[SO_methods.index(SO_priorities[0])]
        orient=get_dictitem(orients,'magic_method_codes',az_type,'has')[0] # re-initialize to best one
    return orient,az_type


def EI(inc):
    poly_tk03= [  3.15976125e-06,  -3.52459817e-04,  -1.46641090e-02,   2.89538539e+00]
    return poly_tk03[0]*inc**3 + poly_tk03[1]*inc**2+poly_tk03[2]*inc+poly_tk03[3]


def find_f(data):
    rad=numpy.pi/180.
    Es,Is,Fs,V2s=[],[],[],[]
    ppars=doprinc(data)
    D=ppars['dec']
    Decs,Incs=data.transpose()[0],data.transpose()[1]
    Tan_Incs=numpy.tan(Incs*rad)
    for f in numpy.arange(1.,.2 ,-.01):
        U=numpy.arctan((1./f)*Tan_Incs)/rad
        fdata=numpy.array([Decs,U]).transpose()
        ppars=doprinc(fdata)
        Fs.append(f)
        Es.append(ppars["tau2"]/ppars["tau3"])
        ang = angle([D,0],[ppars["V2dec"],0])
        if 180.-ang<ang:ang=180.-ang
        V2s.append(ang)
        Is.append(abs(ppars["inc"]))
        if EI(abs(ppars["inc"]))<=Es[-1]:
            del Es[-1]
            del Is[-1]
            del Fs[-1]
            del V2s[-1]
            if len(Fs)>0:
                for f in numpy.arange(Fs[-1],.2 ,-.005):
                    U=numpy.arctan((1./f)*Tan_Incs)/rad
                    fdata=numpy.array([Decs,U]).transpose()
                    ppars=doprinc(fdata)
                    Fs.append(f)
                    Es.append(ppars["tau2"]/ppars["tau3"])
                    Is.append(abs(ppars["inc"]))
                    ang=angle([D,0],[ppars["V2dec"],0])
                    if 180.-ang<ang:ang=180.-ang
                    V2s.append(ang)
                    if EI(abs(ppars["inc"]))<=Es[-1]:
                        return Es,Is,Fs,V2s
    return [0],[0],[0],[0]


def cooling_rate(SpecRec,SampRecs,crfrac,crtype):
    CrSpecRec,frac,crmcd={},0,'DA-CR'
    for key in SpecRec.keys():CrSpecRec[key]=SpecRec[key]
    if len(SampRecs)>0:
        frac=.01*float(SampRecs[0]['cooling_rate_corr'])
        if 'DA-CR' in SampRecs[0]['cooling_rate_mcd']:
            crmcd=SampRecs[0]['cooling_rate_mcd']
        else:
            crmcd='DA-CR'
    elif crfrac!=0:
        frac=crfrac
        crmcd=crtype
    if frac!=0:
        inten=frac*float(CrSpecRec['specimen_int'])
        CrSpecRec["specimen_int"]='%9.4e '%(inten) # adjust specimen intensity by cooling rate correction
        CrSpecRec['magic_method_codes'] = CrSpecRec['magic_method_codes']+':crmcd'
        CrSpecRec["specimen_correction"]='c'
        return CrSpecRec
    else:
        return []


def convert_lat(Recs):
    """
    uses lat, for age<5Ma, model_lat if present, else tries to use average_inc to estimate plat.
    """
    New=[]
    for rec in Recs:
        if 'model_lat' in rec.keys() and rec['model_lat']!="":
             New.append(rec)
        elif 'average_age'  in rec.keys() and rec['average_age']!="" and  float(rec['average_age'])<=5.:
            if 'site_lat' in rec.keys() and rec['site_lat']!="":
                 rec['model_lat']=rec['site_lat']
                 New.append(rec)
        elif 'average_inc' in rec.keys() and rec['average_inc']!="":
            rec['model_lat']='%7.1f'%(plat(float(rec['average_inc'])))
            New.append(rec)
    return New

def convert_ages(Recs):
    """
    converts ages to Ma
    """
    New=[]
    for rec in Recs:
        age=''
        agekey=find('age',rec.keys())
        if agekey!="":
            keybase=agekey.split('_')[0]+'_'
            if rec[keybase+'age']!="":
                age=float(rec[keybase+"age"])
            elif rec[keybase+'age_low']!="" and rec[keybase+'age_high']!='':
                age=float(rec[keybase+'age_low'])  +(float(rec[keybase+'age_high'])-float(rec[keybase+'age_low']))/2.
            if age!='':
                rec[keybase+'age_unit']
                if rec[keybase+'age_unit']=='Ma':
                    rec[keybase+'age']='%10.4e'%(age)
                elif rec[keybase+'age_unit']=='ka' or rec[keybase+'age_unit']=='Ka':
                    rec[keybase+'age']='%10.4e'%(age*.001)
                elif rec[keybase+'age_unit']=='Years AD (+/-)':
                    rec[keybase+'age']='%10.4e'%((2011-age)*1e-6)
                elif rec[keybase+'age_unit']=='Years BP':
                    rec[keybase+'age']='%10.4e'%((age)*1e-6)
                rec[keybase+'age_unit']='Ma'
                New.append(rec)
            else:
                if 'er_site_names' in rec.keys():
                    print 'problem in convert_ages:', rec['er_site_names']
                elif 'er_site_name' in rec.keys():
                    print 'problem in convert_ages:', rec['er_site_name']
                else:
                    print 'problem in convert_ages:', rec
        else:
            print 'no age key:', rec
    return New

def getsampVGP(SampRec,SiteNFO):
    site=get_dictitem(SiteNFO,'er_site_name',SampRec['er_site_name'],'T')
    try:
        lat=float(site['site_lat'])
        lon=float(site['site_lon'])
        dec = float(SampRec['sample_dec'])
        inc = float(SampRec['sample_inc'])
        if SampRec['sample_alpha95']!="":
            a95=float(SampRec['sample_alpha95'])
        else:
            a95=0
        plong,plat,dp,dm=dia_vgp(dec,inc,a95,lat,lon)
        ResRec={}
        ResRec['pmag_result_name']='VGP Sample: '+SampRec['er_sample_name']
        ResRec['er_location_names']=SampRec['er_location_name']
        ResRec['er_citation_names']="This study"
        ResRec['er_site_name']=SampRec['er_site_name']
        ResRec['average_dec']=SampRec['sample_dec']
        ResRec['average_inc']=SampRec['sample_inc']
        ResRec['average_alpha95']=SampRec['sample_alpha95']
        ResRec['tilt_correction']=SampRec['sample_tilt_correction']
        ResRec['pole_comp_name']=SampleRec['sample_comp_name']
        ResRec['vgp_lat']='%7.1f'%(plat)
        ResRec['vgp_lon']='%7.1f'%(plon)
        ResRec['vgp_dp']='%7.1f'%(dp)
        ResRec['vgp_dm']='%7.1f'%(dm)
        ResRec['magic_method_codes']=SampRec['magic_method_codes']+":DE-DI"
        return ResRec
    except:
        return ""

def getsampVDM(SampRec,SampNFO):
    samps=get_dictitem(SampNFO,'er_sample_name',SampRec['er_sample_name'],'T')
    if len(samps)>0:
        samp=samps[0]
        lat=float(samp['sample_lat'])
        int = float(SampRec['sample_int'])
        vdm=b_vdm(int,lat)
        if 'sample_int_sigma' in SampRec.keys() and  SampRec['sample_int_sigma']!="":
            sig=b_vdm(float(SampRec['sample_int_sigma']),lat)
            sig='%8.3e'%(sig)
        else:
            sig=""
    else:
        print 'could not find sample info for: ', SampRec['er_sample_name']
        return {}
    ResRec={}
    ResRec['pmag_result_name']='V[A]DM Sample: '+SampRec['er_sample_name']
    ResRec['er_location_names']=SampRec['er_location_name']
    ResRec['er_citation_names']="This study"
    ResRec['er_site_names']=SampRec['er_site_name']
    ResRec['er_sample_names']=SampRec['er_sample_name']
    if 'sample_dec' in SampRec.keys():
        ResRec['average_dec']=SampRec['sample_dec']
    else:
        ResRec['average_dec']=""
    if 'sample_inc' in SampRec.keys():
        ResRec['average_inc']=SampRec['sample_inc']
    else:
        ResRec['average_inc']=""
    ResRec['average_int']=SampRec['sample_int']
    ResRec['vadm']='%8.3e'%(vdm)
    ResRec['vadm_sigma']=sig
    ResRec['magic_method_codes']=SampRec['magic_method_codes']
    ResRec['model_lat']=samp['sample_lat']
    return ResRec

def getfield(irmunits,coil,treat):
# calibration of ASC Impulse magnetizer
    if coil=="3": m,b=0.0071,-0.004 # B=mh+b where B is in T, treat is in Volts
    if coil=="2": m,b=0.00329,-0.002455 # B=mh+b where B is in T, treat is in Volts
    if coil=="1": m,b=0.0002,-0.0002 # B=mh+b where B is in T, treat is in Volts
    return float(treat)*m+b

def sortbykeys(input,sort_list):
    Output = []
    List=[] # get a list of what to be sorted by second key
    for rec in input:
        if rec[sort_list[0]] not in List:List.append(rec[sort_list[0]])
    for current in List: # step through input finding all records of current
        Currents=[]
        for rec in input:
            if rec[sort_list[0]]==current:Currents.append(rec)
        Current_sorted=sort_diclist(Currents,sort_list[1])
        for rec in Current_sorted:
            Output.append(rec)
    return Output

def get_list(data,key): # return a colon delimited list of unique key values
    keylist=[]
    for rec in data:
        keys=rec[key].split(':')
        for k in keys:
            if k not in keylist:keylist.append(k)
    keystring=""
    if len(keylist)==0:return keystring
    for k in keylist:keystring=keystring+':'+k
    return keystring[1:]

def ParseSiteFile(site_file):
    Sites,file_type=magic_read(site_file)
    LocNames,Locations=[],[]
    for site in Sites:
        if site['er_location_name'] not in LocNames: # new location name
            LocNames.append(site['er_location_name'])
            sites_locs=get_dictitem(Sites,'er_location_name',site['er_location_name'],'T') # get all sites for this loc
            lats=get_dictkey(sites_locs,'site_lat','f') # get all the latitudes as floats
            lons=get_dictkey(sites_locs,'site_lon','f') # get all the longitudes as floats
            LocRec={'er_citation_names':'This study','er_location_name':site['er_location_name'],'location_type':''}
            LocRec['location_begin_lat']=str(min(lats))
            LocRec['location_end_lat']=str(max(lats))
            LocRec['location_begin_lon']=str(min(lons))
            LocRec['location_end_lon']=str(max(lons))
            Locations.append(LocRec)
    return Locations

def ParseMeasFile(measfile,sitefile,instout,specout): # fix up some stuff for uploading
    #
    # read in magic_measurements file to get specimen, and instrument names
    #
    master_instlist=[]
    InstRecs=[]
    meas_data,file_type=magic_read(measfile)
    if file_type != 'magic_measurements':
        print file_type,"This is not a valid magic_measurements file "
        sys.exit()
    # read in site data
    if sitefile!="":
        SiteNFO,file_type=magic_read(sitefile)
        if file_type=="bad_file":
            print "Bad  or no er_sites file - lithology, etc will not be imported"
    else:
        SiteNFO=[]
    # define the Er_specimen records to create a new er_specimens.txt file
    #
    suniq,ErSpecs=[],[]
    for rec in meas_data:
# fill in some potentially missing fields
        if "magic_instrument_codes" in rec.keys():
            list=(rec["magic_instrument_codes"])
            list.strip()
            tmplist=list.split(":")
            for inst in tmplist:
                if inst not in master_instlist:
                    master_instlist.append(inst)
                    InstRec={}
                    InstRec["magic_instrument_code"]=inst
                    InstRecs.append(InstRec)
        if "measurement_standard" not in rec.keys():rec['measurement_standard']='u' # make this an unknown if not specified
        if rec["er_specimen_name"] not in suniq and rec["measurement_standard"]!='s': # exclude standards
            suniq.append(rec["er_specimen_name"])
            ErSpecRec={}
            ErSpecRec["er_citation_names"]="This study"
            ErSpecRec["er_specimen_name"]=rec["er_specimen_name"]
            ErSpecRec["er_sample_name"]=rec["er_sample_name"]
            ErSpecRec["er_site_name"]=rec["er_site_name"]
            ErSpecRec["er_location_name"]=rec["er_location_name"]
    #
    # attach site litho, etc. to specimen if not already there
            sites=get_dictitem(SiteNFO,'er_site_name',rec['er_site_name'],'T')
            if len(sites)==0:
                site={}
                print 'site record in er_sites table not found for: ',rec['er_site_name']
            else:
                site=sites[0]
            if 'site_class' not in site.keys() or 'site_lithology' not in site.keys() or 'site_type' not in site.keys():
                site['site_class']='Not Specified'
                site['site_lithology']='Not Specified'
                site['site_type']='Not Specified'
            if 'specimen_class' not in ErSpecRec.keys():ErSpecRec["specimen_class"]=site['site_class']
            if 'specimen_lithology' not in ErSpecRec.keys():ErSpecRec["specimen_lithology"]=site['site_lithology']
            if 'specimen_type' not in ErSpecRec.keys():ErSpecRec["specimen_type"]=site['site_type']
            if 'specimen_volume' not in ErSpecRec.keys():ErSpecRec["specimen_volume"]=""
            if 'specimen_weight' not in ErSpecRec.keys():ErSpecRec["specimen_weight"]=""
            ErSpecs.append(ErSpecRec)
    #
    #
    # save the data
    #
    magic_write(specout,ErSpecs,"er_specimens")
    print " Er_Specimen data (with updated info from site if necessary)  saved in ",specout
    #
    # write out the instrument list
    if len(InstRecs) >0:
        magic_write(instout,InstRecs,"magic_instruments")
        print " Instruments data saved in ",instout
    else:
        print "No instruments found"

def ReorderSamples(specfile,sampfile,outfile): # take care of re-ordering sample table, putting used orientations first
    UsedSamps,RestSamps=[],[]
    Specs,filetype=magic_read(specfile) # read in specimen file
    Samps,filetype=magic_read(sampfile) # read in sample file
    for rec in Specs: # hunt through specimen by specimen
        meths=rec['magic_method_codes'].strip().strip('\n').split(':')
        for meth in meths:
            methtype=meth.strip().strip('\n').split('-')
            if 'SO' in methtype:
                SO_meth=meth # find the orientation method code
        samprecs=get_dictitem(Samps,'er_sample_name',rec['er_sample_name'],'T')
        used=get_dictitem(samprecs,'magic_method_codes',SO_meth,'has')
        if len(used)>0:
            UsedSamps.append(used[0])
        else:
            print 'orientation not found for: ',rec['er_specimen_name']
        rest=get_dictitem(samprecs,'magic_method_codes',SO_meth,'not')
        for rec in rest:
            RestSamps.append(rec)
    for rec in RestSamps:
        UsedSamps.append(rec) # append the unused ones to the end of the file
    magic_write(outfile,UsedSamps,'er_samples')

def orient(mag_azimuth,field_dip,or_con):
    """
    uses specified orientation convention to convert user supplied orientations
    to laboratory azimuth and plunge
    """
    or_con = str(or_con)
    if mag_azimuth==-999:return "",""
    if or_con=="1": # lab_mag_az=mag_az;  sample_dip = -dip
        return mag_azimuth, -field_dip
    if or_con=="2":
        return mag_azimuth-90.,-field_dip
    if or_con=="3": # lab_mag_az=mag_az;  sample_dip = 90.-dip
        return mag_azimuth, 90.-field_dip
    if or_con=="4": # lab_mag_az=mag_az;  sample_dip = dip
        return mag_azimuth, field_dip
    if or_con=="5": # lab_mag_az=mag_az;  sample_dip = dip-90.
        return mag_azimuth, field_dip-90.
    if or_con=="6": # lab_mag_az=mag_az-90.;  sample_dip = 90.-dip
        return mag_azimuth-90., 90.-field_dip
    if or_con=="7": # lab_mag_az=mag_az;  sample_dip = 90.-dip
        return mag_azimuth-90., 90.-field_dip
    print "Error in orientation convention"

def get_Sb(data):
    """
    returns vgp scatter for data set
    """
    Sb,N=0.,0.
    for  rec in data:
                delta=90.-abs(float(rec['vgp_lat']))
                if rec['average_k']!="0":
                    k=float(rec['average_k'])
                    L=float(rec['average_lat'])*numpy.pi/180. # latitude in radians
                    Nsi=float(rec['average_nn'])
                    K=k/(2.*(1.+3.*numpy.sin(L)**2)/(5.-3.*numpy.sin(L)**2))
                    Sw=81./numpy.sqrt(K)
                else:
                    Sw,Nsi=0,1.
                Sb+=delta**2.-(Sw**2)/Nsi
                N+=1.
    return numpy.sqrt( Sb/float(N-1.) )

def default_criteria(nocrit):
    Crits={}
    critkeys=['magic_experiment_names', 'measurement_step_min', 'measurement_step_max', 'measurement_step_unit', 'specimen_polarity', 'specimen_nrm', 'specimen_direction_type', 'specimen_comp_nmb', 'specimen_mad', 'specimen_alpha95', 'specimen_n', 'specimen_int_sigma', 'specimen_int_sigma_perc', 'specimen_int_rel_sigma', 'specimen_int_rel_sigma_perc', 'specimen_int_mad', 'specimen_int_n', 'specimen_w', 'specimen_q', 'specimen_f', 'specimen_fvds', 'specimen_b_sigma', 'specimen_b_beta', 'specimen_g', 'specimen_dang', 'specimen_md', 'specimen_ptrm', 'specimen_drat', 'specimen_drats', 'specimen_rsc', 'specimen_viscosity_index', 'specimen_magn_moment', 'specimen_magn_volume', 'specimen_magn_mass', 'specimen_int_dang','specimen_int_ptrm_n', 'specimen_delta', 'specimen_theta', 'specimen_gamma', 'specimen_frac','specimen_gmax','specimen_scat','sample_polarity', 'sample_nrm', 'sample_direction_type', 'sample_comp_nmb', 'sample_sigma', 'sample_alpha95', 'sample_n', 'sample_n_lines', 'sample_n_planes', 'sample_k', 'sample_r', 'sample_tilt_correction', 'sample_int_sigma', 'sample_int_sigma_perc', 'sample_int_rel_sigma', 'sample_int_rel_sigma_perc', 'sample_int_n', 'sample_magn_moment', 'sample_magn_volume', 'sample_magn_mass', 'site_polarity', 'site_nrm', 'site_direction_type', 'site_comp_nmb', 'site_sigma', 'site_alpha95', 'site_n', 'site_n_lines', 'site_n_planes', 'site_k', 'site_r', 'site_tilt_correction', 'site_int_sigma', 'site_int_sigma_perc', 'site_int_rel_sigma', 'site_int_rel_sigma_perc', 'site_int_n', 'site_magn_moment', 'site_magn_volume', 'site_magn_mass', 'average_age_min', 'average_age_max', 'average_age_sigma', 'average_age_unit', 'average_sigma', 'average_alpha95', 'average_n', 'average_nn', 'average_k', 'average_r', 'average_int_sigma', 'average_int_rel_sigma', 'average_int_rel_sigma_perc', 'average_int_n', 'average_int_nn', 'vgp_dp', 'vgp_dm', 'vgp_sigma', 'vgp_alpha95', 'vgp_n', 'vdm_sigma', 'vdm_n', 'vadm_sigma', 'vadm_n', 'criteria_description', 'er_citation_names']
    for key in critkeys:Crits[key]='' # set up dictionary with all possible
    Crits['pmag_criteria_code']='ACCEPT'
    Crits['criteria_definition']='acceptance criteria for study'
    Crits['er_citation_names']='This study'
    if nocrit==0: # use default criteria
#
# set some sort of quasi-reasonable default criteria
#
        Crits['specimen_mad']='5'
        Crits['specimen_dang']='10'
        Crits['specimen_int_n']='4'
        Crits['specimen_int_ptrm_n']='2'
        Crits['specimen_drats']='20'
        Crits['specimen_b_beta']='0.1'
        Crits['specimen_md']='15'
        Crits['specimen_fvds']='0.7'
        Crits['specimen_q']='1.0'
        Crits['specimen_int_dang']='10'
        Crits['specimen_int_mad']='10'
        Crits['sample_alpha95']='5'
        Crits['site_int_n']='2'
        Crits['site_int_sigma']='5e-6'
        Crits['site_int_sigma_perc']='15'
        Crits['site_n']='5'
        Crits['site_n_lines']='4'
        Crits['site_k']='50'
    return [Crits]

def grade(PmagRec,ACCEPT,type):
    """
    Finds the 'grade' (pass/fail; A/F) of a record (specimen,sample,site) given the acceptance criteria
    """
    GREATERTHAN=['specimen_q','site_k','site_n','site_n_lines','site_int_n','measurement_step_min','specimen_int_ptrm_n','specimen_fvds','specimen_frac','specimen_f','specimen_n','specimen_int_n','sample_int_n','average_age_min','average_k','average_r','specimen_magn_moment','specimen_magn_volumn','specimen_rsc','sample_n','sample_n_lines','sample_n_planes','sample_k','sample_r','site_magn_moment','site_magn_volumn','site_magn_mass','site_r'] # these statistics must be exceede to pass, all others must be less than (except specimen_scat, which must be true)
    ISTRUE=['specimen_scat']
    kill=[] # criteria that kill the record
    sigma_types=['sample_int_sigma','sample_int_sigma_perc','site_int_sigma','site_int_sigma_perc','average_int_sigma','average_int_sigma_perc']
    sigmas=[]
    accept={}
    if type=='specimen_int':
        USEKEYS=['specimen_q','measurement_step_min','measurement_step_max','specimen_int_ptrm_n','specimen_fvds','specimen_frac','specimen_f','specimen_int_n','specimen_magn_moment','specimen_magn_volumn','specimen_rsc','specimen_scat','specimen_drats','specimen_int_mad','specimen_int_dang','specimen_md','specimen_b_beta','specimen_w','specimen_gmax']
    elif type=='specimen_dir':
        USEKEYS=['measurement_step_min','measurement_step_max','specimen_mad','specimen_n','specimen_magn_moment','specimen_magn_volumn']
    elif type=='sample_int':
        USEKEYS=['sample_int_n','sample_int_sigma','sample_int_sigma_perc']
    elif type=='sample_dir':
        USEKEYS=['sample_alpha95','sample_n','sample_n_lines','sample_n_planes','sample_k','sample_r']
    elif type=='site_int':
        USEKEYS=['site_int_sigma','site_int_sigma_perc','site_int_n']
    elif type=='site_dir':
        USEKEYS=['site_alpha95','site_k','site_n','site_n_lines','site_n_planes','site_r']

    for key in ACCEPT.keys():
        if ACCEPT[key]!="" and key in USEKEYS:
            if key in ISTRUE and ACCEPT[key]=='TRUE' or ACCEPT[key]=='True':
                ACCEPT[key]='1' # this is because Excel always capitalizes True to TRUE and python doesn't recognize that as a boolean.  never mind
            elif ACCEPT[key]=='FALSE' or ACCEPT[key]=='False':
                ACCEPT[key]='0'
            elif eval(ACCEPT[key])==0:
                ACCEPT[key]=""
            accept[key]=ACCEPT[key]
    for key in sigma_types:
        if key in USEKEYS and key in accept.keys() and key in PmagRec.keys(): sigmas.append(key)
    if len(sigmas)>1:
        if PmagRec[sigmas[0]]=="" or PmagRec[sigmas[1]]=="":
           kill.append(sigmas[0])
           kill.append(sigmas[1])
        elif eval(PmagRec[sigmas[0]])>eval(accept[sigmas[0]]) and eval(PmagRec[sigmas[1]])>eval(accept[sigmas[1]]):
           kill.append(sigmas[0])
           kill.append(sigmas[1])
    elif len(sigmas)==1 and sigmas[0] in accept.keys():
        if PmagRec[sigmas[0]]>accept[sigmas[0]]:
           kill.append(sigmas[0])
    for key in accept.keys():
     if accept[key]!="":
        if key not in PmagRec.keys() or PmagRec[key]=='':
            kill.append(key)
        elif key not in sigma_types:
            if key in ISTRUE: # boolean must be true
                if PmagRec[key]!='1':
                    kill.append(key)
            if key in GREATERTHAN:
                if eval(PmagRec[key])<eval(accept[key]):
                    kill.append(key)
            else:
                if eval(PmagRec[key])>eval(accept[key]):
                    kill.append(key)
    return kill

#
def flip(D):
    """
    determines principle direction and calculates the antipode of
    the reverse mode

    input: a nested list of directions
    returns a normal mode and flipped reverse mode as two DI blocks
    """
    ppars=doprinc(D) #get principle direction
    D1,D2=[],[]
    for rec in D:
        ang=angle([rec[0],rec[1]],[ppars['dec'],ppars['inc']])
        if ang>90.:
            d,i=(rec[0]-180.)%360.,-rec[1]
            D2.append([d,i,1.])
        else:
            D1.append([rec[0],rec[1],1.])
    return D1,D2
#
def dia_vgp(*args): # new function interface by J.Holmes, SIO, 6/1/2011
    """
    converts declination, inclination, alpha95 to VGP, dp, dm
    takes input as (Decs, Incs, a95, Site latitudes, Site Longitudes).
    These can be lists or individual values.
    Returns longitude, latitude, dp, dm
    """
    # test whether arguments are one 2-D list or 5 floats
    if len(args) == 1: # args comes in as a tuple of multi-dim lists.
        largs=list(args).pop() # scrap the tuple.
        (decs, dips, a95s, slats, slongs) = zip(*largs) # reorganize the lists so that we get columns of data in each var.
    else:
        # When args > 1, we are receiving five floats. This usually happens when the invoking script is
        # executed in interactive mode.
        (decs, dips, a95s, slats, slongs) = (args)

    # We send all incoming data to numpy in an array form. Even if it means a 1x1 matrix. That's OKAY. Really.
    (dec, dip, a95, slat, slong) = (numpy.array(decs), numpy.array(dips), numpy.array(a95s), \
                                    numpy.array(slats), numpy.array(slongs)) # package columns into arrays
    rad=numpy.pi/180. # convert to radians
    dec,dip,a95,slat,slong=dec*rad,dip*rad,a95*rad,slat*rad,slong*rad
    p=numpy.arctan2(2.0,numpy.tan(dip))
    plat=numpy.arcsin(numpy.sin(slat)*numpy.cos(p)+numpy.cos(slat)*numpy.sin(p)*numpy.cos(dec))
    beta=(numpy.sin(p)*numpy.sin(dec))/numpy.cos(plat)

    #------------------------------------------------------------------------------------------------------------
    # The deal with "boolmask":
    # We needed a quick way to assign matrix values based on a logic decision, in this case setting boundaries
    # on out-of-bounds conditions. Creating a matrix of boolean values the size of the original matrix and using
    # it to "mask" the assignment solves this problem nicely. The downside to this is that Numpy complains if you
    # attempt to mask a non-matrix, so we have to check for array type and do a normal assignment if the type is
    # scalar. These checks are made before calculating for the rest of the function.
    #------------------------------------------------------------------------------------------------------------

    boolmask = beta > 1. # create a mask of boolean values
    if isinstance(beta,numpy.ndarray):
        beta[boolmask] = 1. # assigns 1 only to elements that mask TRUE.
    else: # Numpy gets upset if you try our masking trick with a scalar or a 0-D matrix.
        if boolmask:
            beta = 1.
    boolmask = beta < -1.
    if isinstance(beta,numpy.ndarray):
        beta[boolmask] = -1. # assigns -1 only to elements that mask TRUE.
    else:
        if boolmask:
            beta = -1.

    beta=numpy.arcsin(beta)
    plong = slong+numpy.pi-beta
    if (numpy.cos(p) > numpy.sin(slat)*numpy.sin(plat)).any():
        boolmask = (numpy.cos(p) > (numpy.sin(slat)*numpy.sin(plat)))
        if isinstance(plong,numpy.ndarray):
            plong[boolmask] = (slong+beta)[boolmask]
        else:
            if boolmask:
                plong = slong+beta

    boolmask = (plong < 0)
    if isinstance(plong,numpy.ndarray):
        plong[boolmask] = plong[boolmask]+2*numpy.pi
    else:
        if boolmask:
            plong = plong+2*numpy.pi

    boolmask = (plong > 2*numpy.pi)
    if isinstance(plong,numpy.ndarray):
        plong[boolmask] = plong[boolmask]-2*numpy.pi
    else:
        if boolmask:
            plong = plong-2*numpy.pi

    dm=a95* (numpy.cos(slat)/numpy.cos(dip))/rad
    dp=a95*(1+3*(numpy.sin(slat)**2))/(2*rad)
    plat,plong=plat/rad,plong/rad
    return plong.tolist(),plat.tolist(),dp.tolist(),dm.tolist()

def int_pars(x,y,vds):
    """
     calculates York regression and Coe parameters (with Tauxe Fvds)
    """
# first do linear regression a la York
    xx,yer,xer,xyer,yy,xsum,ysum,xy=0.,0.,0.,0.,0.,0.,0.,0.
    xprime,yprime=[],[]
    pars={}
    pars["specimen_int_n"]=len(x)
    n=float(len(x))
    if n<=2:
        print "shouldn't be here at all!"
        return pars,1
    for i in range(len(x)):
        xx+=x[i]**2.
        yy+=y[i]**2.
        xy+=x[i]*y[i]
        xsum+=x[i]
        ysum+=y[i]
    xsig=numpy.sqrt((xx-(xsum**2./n))/(n-1.))
    ysig=numpy.sqrt((yy-(ysum**2./n))/(n-1.))
    sum=0
    for i in range(int(n)):
        yer+= (y[i]-ysum/n)**2.
        xer+= (x[i]-xsum/n)**2.
        xyer+= (y[i]-ysum/n)*(x[i]-xsum/n)
    slop=-numpy.sqrt(yer/xer)
    pars["specimen_b"]=slop
    s1=2.*yer-2.*slop*xyer
    s2=(n-2.)*xer
    sigma=numpy.sqrt(s1/s2)
    pars["specimen_b_sigma"]=sigma
    s=(xy-(xsum*ysum/n))/(xx-(xsum**2.)/n)
    r=(s*xsig)/ysig
    pars["specimen_rsc"]=r**2.
    ytot=abs(ysum/n-slop*xsum/n)
    for i in range(int(n)):
        xprime.append((slop*x[i]+y[i]-ytot)/(2.*slop))
        yprime.append(((slop*x[i]+y[i]-ytot)/2.)+ytot)
    sumdy,dy=0,[]
    dyt = abs(yprime[0]-yprime[int(n)-1])
    for i in range((int(n)-1)):
        dy.append(abs(yprime[i+1]-yprime[i]))
        sumdy+= dy[i]**2.
    f=dyt/ytot
    pars["specimen_f"]=f
    pars["specimen_ytot"]=ytot
    ff=dyt/vds
    pars["specimen_fvds"]=ff
    ddy=(1./dyt)*sumdy
    g=1.-ddy/dyt
    pars["specimen_g"]=g
    q=abs(slop)*f*g/sigma
    pars["specimen_q"]=q
    pars["specimen_b_beta"]=-sigma/slop
    return pars,0

def dovds(data):
    """
     calculates vector difference sum for demagnetization data
    """
    vds,X=0,[]
    for rec in data:
        X.append(dir2cart(rec))
    for k  in range(len(X)-1):
        xdif=X[k+1][0]-X[k][0]
        ydif=X[k+1][1]-X[k][1]
        zdif=X[k+1][2]-X[k][2]
        vds+=numpy.sqrt(xdif**2+ydif**2+zdif**2)
    vds+=numpy.sqrt(X[-1][0]**2+X[-1][1]**2+X[-1][2]**2)
    return vds

def vspec_magic(data):
    """
   takes average vector of replicate measurements
    """
    vdata,Dirdata,step_meth=[],[],""
    if len(data)==0:return vdata
    treat_init=["treatment_temp", "treatment_temp_decay_rate", "treatment_temp_dc_on", "treatment_temp_dc_off", "treatment_ac_field", "treatment_ac_field_decay_rate", "treatment_ac_field_dc_on", "treatment_ac_field_dc_off", "treatment_dc_field", "treatment_dc_field_decay_rate", "treatment_dc_field_ac_on", "treatment_dc_field_ac_off", "treatment_dc_field_phi", "treatment_dc_field_theta"]
    treats=[]
#
# find keys that are used
#
    for key in treat_init:
        if key in data[0].keys():treats.append(key)  # get a list of keys
    stop={}
    stop["er_specimen_name"]="stop"
    for key in treats:
        stop[key]="" # tells program when to quit and go home
    data.append(stop)
#
# set initial states
#
    DataState0,newstate={},0
    for key in treats:
        DataState0[key]=data[0][key] # set beginning treatment
    k,R=1,0
    for i in range(k,len(data)):
        FDirdata,Dirdata,DataStateCurr,newstate=[],[],{},0
        for key in treats:  # check if anything changed
	    DataStateCurr[key]=data[i][key]
            if DataStateCurr[key].strip() !=  DataState0[key].strip(): newstate=1 # something changed
        if newstate==1:
            if i==k: # sample is unique
                vdata.append(data[i-1])
            else: # measurement is not unique
                #print "averaging: records " ,k,i
                for l in range(k-1,i):
                    if 'orientation' in data[l]['measurement_description']:
                        data[l]['measurement_description']=""
                    Dirdata.append([float(data[l]['measurement_dec']),float(data[l]['measurement_inc']),float(data[l]['measurement_magn_moment'])])
                    FDirdata.append([float(data[l]['measurement_dec']),float(data[l]['measurement_inc'])])
                dir,R=vector_mean(Dirdata)
                Fpars=fisher_mean(FDirdata)
                vrec=data[i-1]
                vrec['measurement_dec']='%7.1f'%(dir[0])
                vrec['measurement_inc']='%7.1f'%(dir[1])
                vrec['measurement_magn_moment']='%8.3e'%(R/(i-k+1))
                vrec['measurement_csd']='%7.1f'%(Fpars['csd'])
                vrec['measurement_positions']='%7.1f'%(Fpars['n'])
                vrec['measurement_description']='average of multiple measurements'
                if "magic_method_codes" in vrec.keys():
                    meths=vrec["magic_method_codes"].strip().split(":")
                    if "DE-VM" not in meths:meths.append("DE-VM")
                    methods=""
                    for meth in meths:
                        methods=methods+meth+":"
                    vrec["magic_method_codes"]=methods[:-1]
                else: vrec["magic_method_codes"]="DE-VM"
                vdata.append(vrec)
# reset state to new one
            for key in treats:
                DataState0[key]=data[i][key] # set beginning treatment
            k=i+1
            if data[i]["er_specimen_name"] =="stop":
                del data[-1]  # get rid of dummy stop sign
                return vdata,treats # bye-bye

def get_specs(data):
    """
     takes a magic format file and returns a list of unique specimen names
    """
# sort the specimen names
#
    speclist=[]
    for rec in data:
      spec=rec["er_specimen_name"]
      if spec not in speclist:
          speclist.append(spec)
    speclist.sort()
    return speclist

def vector_mean(data):
    """
    calculates the vector mean of a given set of vectors
    """
    R,Xbar,X=0,[0,0,0],[]
    for rec in data:
        X.append(dir2cart(rec))
    for i in range(len(X)):
        for c in range(3):
           Xbar[c]+=X[i][c]
    for c in range(3):
        R+=Xbar[c]**2
    R=numpy.sqrt(R)
    for c in range(3):
        Xbar[c]=Xbar[c]/R
    dir=cart2dir(Xbar)
    return dir, R

def mark_dmag_rec(s,ind,data):
    """
    edits demagnetization data to mark "bad" points with measurement_flag
    """
    datablock=[]
    for rec in  data:
        if rec['er_specimen_name']==s:
            meths=rec['magic_method_codes'].split(':')
            if 'LT-NO' in meths or 'LT-AF-Z' in meths or 'LT-T-Z' in meths:
                datablock.append(rec)
    dmagrec=datablock[ind]
    for k in  range(len(data)):
        meths=data[k]['magic_method_codes'].split(':')
        if 'LT-NO' in meths or 'LT-AF-Z' in meths or 'LT-T-Z' in meths:
            if data[k]['er_specimen_name']==s:
                if data[k]['treatment_temp']==dmagrec['treatment_temp'] and data[k]['treatment_ac_field']==dmagrec['treatment_ac_field']:
                    if data[k]['measurement_dec']==dmagrec['measurement_dec'] and data[k]['measurement_inc']==dmagrec['measurement_inc'] and data[k]['measurement_magn_moment']==dmagrec['measurement_magn_moment']:
                        if data[k]['measurement_flag']=='g':
                            flag='b'
                        else:
                            flag='g'
                        data[k]['measurement_flag']=flag
                        break
    return data

def mark_samp(Samps,data,crd):




    return Samps

def find_dmag_rec(s,data):
    """
    returns demagnetization data for specimen s from the data - excludes other kinds of experiments and "bad" measurements
    """
    EX=["LP-AN-ARM","LP-AN-TRM","LP-ARM-AFD","LP-ARM2-AFD","LP-TRM-AFD","LP-TRM","LP-TRM-TD","LP-X"] # list of excluded lab protocols
    INC=["LT-NO","LT-AF-Z","LT-T-Z", "LT-M-Z", "LP-PI-TRM-IZ", "LP-PI-M-IZ"]
    datablock,tr=[],""
    therm_flag,af_flag,mw_flag=0,0,0
    units=[]
    spec_meas=get_dictitem(data,'er_specimen_name',s,'T')
    for rec in spec_meas:
           if 'measurement_flag' not in rec.keys():rec['measurement_flag']='g'
           skip=1
           tr=""
           methods=rec["magic_method_codes"].split(":")
           for meth in methods:
               if meth.strip() in INC:
                   skip=0
           for meth in EX:
               if meth in methods:skip=1
           if skip==0:
               if "LT-NO" in methods:
                   tr = float(rec["treatment_temp"])
               if "LT-AF-Z" in methods:
                   af_flag=1
                   tr = float(rec["treatment_ac_field"])
                   if "T" not in units:units.append("T")
               if "LT-T-Z" in methods:
                   therm_flag=1
                   tr = float(rec["treatment_temp"])
                   if "K" not in units:units.append("K")
               if "LT-M-Z" in methods:
                   mw_flag=1
                   tr = float(rec["treatment_mw_power"])*float(rec["treatment_mw_time"])
                   if "J" not in units:units.append("J")
               if "LP-PI-TRM-IZ" in methods or "LP-PI-M-IZ" in methods:  # looking for in-field first thellier or microwave data - otherwise, just ignore this
                   ZI=0
               else:
                   ZI=1
               Mkeys=['measurement_magnitude','measurement_magn_moment','measurement_magn_volume','measurement_magn_mass']
               if tr !="":
                   dec,inc,int = "","",""
                   if "measurement_dec" in rec.keys() and rec["measurement_dec"] != "":
                       dec=float(rec["measurement_dec"])
                   if "measurement_inc" in rec.keys() and rec["measurement_inc"] != "":
                       inc=float(rec["measurement_inc"])
                   for key in Mkeys:
                       if key in rec.keys() and rec[key]!="":int=float(rec[key])
                   if 'magic_instrument_codes' not in rec.keys():rec['magic_instrument_codes']=''
                   datablock.append([tr,dec,inc,int,ZI,rec['measurement_flag'],rec['magic_instrument_codes']])
    if therm_flag==1:
        for k in range(len(datablock)):
            if datablock[k][0]==0.: datablock[k][0]=273.
    if af_flag==1:
        for k in range(len(datablock)):
            if datablock[k][0]>=273 and datablock[k][0]<=323: datablock[k][0]=0.
    meas_units=""
    if len(units)>0:
        for u in units:meas_units=meas_units+u+":"
        meas_units=meas_units[:-1]
    return datablock,meas_units

def magic_read(infile, data=None):
    """
    reads  a Magic template file, puts data in a list of dictionaries.
    """
    hold,magic_data,magic_record,magic_keys=[],[],{},[]
    if data: #
        f = data
    else:
        try:
            f=open(infile,"rU")
        except:
            return [],'bad_file'

    d = f.readline()[:-1].strip('\n')
    if not d:
        return [], 'empty_file'
    if d[0]=="s" or d[1]=="s":
        delim='space'
    elif d[0]=="t" or d[1]=="t":
        delim='tab'
    else:
        print 'error reading ', infile
        #sys.exit()
        return [], 'bad_file'
    if delim=='space':
        file_type=d.split()[1]
    if delim=='tab':
        file_type=d.split('\t')[1]
    if file_type=='delimited':
        if delim=='space':
            file_type=d.split()[2]
        if delim=='tab':
            file_type=d.split('\t')[2]
    if delim=='space':
        line =f.readline()[:-1].split()
    if delim=='tab':
        line =f.readline()[:-1].split('\t')
    for key in line:
        magic_keys.append(key)
    lines=f.readlines()
    if len(lines)<1:
       return [],'empty_file'
    for line in lines[:-1]:
        line.replace('\n','')
        if delim=='space':rec=line[:-1].split()
        if delim=='tab':rec=line[:-1].split('\t')
        hold.append(rec)
    line = lines[-1].replace('\n','')
    if delim=='space':rec=line[:-1].split()
    if delim=='tab':rec=line.split('\t')
    hold.append(rec)
    for rec in hold:
        magic_record={}
        if len(magic_keys) != len(rec):
            if rec != ['>>>>>>>>>>'] and 'delimited' not in rec[0]: # ignores this warning when reading the dividers in an upload.txt composite file
                print "Warning: Uneven record lengths detected: "
                print magic_keys
                print rec
        # modified by Ron Shaar:
        # add a health check:
        # if len(magic_keys) > len(rec): take rec
        # if len(magic_keys) < len(rec): take magic_keys
        # original code: for k in range(len(rec)):
        # channged to: for k in range(min(len(magic_keys),len(rec))):
        for k in range(min(len(magic_keys),len(rec))):
           magic_record[magic_keys[k]]=rec[k].strip('\n')
        magic_data.append(magic_record)
    magictype=file_type.lower().split("_")
    Types=['er','magic','pmag','rmag']
    if magictype in Types:file_type=file_type.lower()
    return magic_data,file_type

def upload_read(infile,table):
    """
    reads  a table from a MagIC upload (or downloaded) txt file,
     puts data in a list of dictionaries
    """
    delim='tab'
    hold,magic_data,magic_record,magic_keys=[],[],{},[]
    f=open(infile,"rU")
#
# look for right table
#
    line =f.readline()[:-1]
    file_type=line.split('\t')[1]
    if file_type=='delimited': file_type=line.split('\t')[2]
    if delim=='tab':
        line =f.readline()[:-1].split('\t')
    else:
        print "only tab delimitted files are supported now"
        sys.exit()
    while file_type!=table:
        while line[0][0:5] in f.readlines() !=">>>>>":
            pass
        line =f.readline()[:-1]
        file_type=line.split('\t')[1]
        if file_type=='delimited': file_type=line.split('\t')[2]
        ine =f.readline()[:-1].split('\t')
    while line[0][0:5] in f.readlines() !=">>>>>":
        for key in line:
            magic_keys.append(key)
        for line in f.readlines():
            rec=line[:-1].split('\t')
            hold.append(rec)
        for rec in hold:
            magic_record={}
            if len(magic_keys) != len(rec):
                print "Uneven record lengths detected: ",rec
                raw_input("Return to continue.... ")
            for k in range(len(magic_keys)):
                magic_record[magic_keys[k]]=rec[k]
            magic_data.append(magic_record)
    return magic_data

def putout(ofile,keylist,Rec):
    """
    writes out a magic format record to ofile
    """
    pmag_out=open(ofile,'a')
    outstring=""
    for key in keylist:
        try:
           outstring=outstring + '\t' + str(Rec[key]).strip()
        except:
           print key,Rec[key]
           #raw_input()
    outstring=outstring+'\n'
    pmag_out.write(outstring[1:])
    pmag_out.close()

def first_rec(ofile,Rec,file_type):
    """
    opens the file ofile as a magic template file with headers as the keys to Rec
    """
    keylist=[]
    opened = False
    # sometimes Windows needs a little extra time to open a file
    # or else it throws an error
    while not opened:
        try:
            pmag_out = open(ofile,'w')
            opened = True
        except IOError:
            time.sleep(1)
    outstring="tab \t"+file_type+"\n"
    pmag_out.write(outstring)
    keystring=""
    for key in Rec.keys():
        keystring=keystring+'\t'+key.strip()
        keylist.append(key)
    keystring=keystring + '\n'
    pmag_out.write(keystring[1:])
    pmag_out.close()
    return keylist

def magic_write_old(ofile,Recs,file_type):
    """
    writes out a magic format list of dictionaries to ofile
    """

    if len(Recs)<1:
        return
    pmag_out=open(ofile,'w')
    outstring="tab \t"+file_type+"\n"
    pmag_out.write(outstring)
    keystring=""
    keylist=[]
    for key in Recs[0].keys():
        keylist.append(key)
    keylist.sort()
    for key in keylist:
        keystring=keystring+'\t'+key.strip()
    keystring=keystring + '\n'
    pmag_out.write(keystring[1:])
    for Rec in Recs:
        outstring=""
        for key in keylist:
           try:
              outstring=outstring+'\t'+str(Rec[key].strip())
           except:
              if 'er_specimen_name' in Rec.keys():
                  print Rec['er_specimen_name']
              elif 'er_specimen_names' in Rec.keys():
                  print Rec['er_specimen_names']
              print key,Rec[key]
              #raw_input()
        outstring=outstring+'\n'
        pmag_out.write(outstring[1:])
    pmag_out.close()

def magic_write(ofile,Recs,file_type):
    """
    called by magic_write(outputfile,records_list,magic_file_type)
    writes out a magic format list of dictionaries to ofile

    """
    if len(Recs)<1:
        return False, 'No records to write to file {}'.format(ofile)
    else:
        print len(Recs),' records written to file ',ofile
    pmag_out=open(ofile,'w')
    outstring="tab \t"+file_type+"\n"
    pmag_out.write(outstring)
    keystring=""
    keylist=[]
    for key in Recs[0].keys():
        keylist.append(key)
    keylist.sort()
    for key in keylist:
        keystring=keystring+'\t'+key.strip()
    keystring=keystring + '\n'
    pmag_out.write(keystring[1:])
    for Rec in Recs:
        outstring=""
        for key in keylist:
           try:
              outstring=outstring+'\t'+str(Rec[key].strip())
           except:
              if 'er_specimen_name' in Rec.keys():
                  print Rec['er_specimen_name']
              elif 'er_specimen_names' in Rec.keys():
                  print Rec['er_specimen_names']
              print key,Rec[key]
              #raw_input()
        outstring=outstring+'\n'
        pmag_out.write(outstring[1:])
    pmag_out.close()
    return True, ofile

def dotilt(dec,inc,bed_az,bed_dip):
    """
    does a tilt correction on dec,inc using bedding dip direction bed_az and dip bed_dip.  called with syntax:  dotilt(dec,inc,bed_az,bed_dip).
    """
    rad=numpy.pi/180. # converts from degrees to radians
    X=dir2cart([dec,inc,1.]) # get cartesian coordinates of dec,inc
# get some sines and cosines of new coordinate system
    sa,ca= -numpy.sin(bed_az*rad),numpy.cos(bed_az*rad)
    cdp,sdp= numpy.cos(bed_dip*rad),numpy.sin(bed_dip*rad)
# do the rotation
    xc=X[0]*(sa*sa+ca*ca*cdp)+X[1]*(ca*sa*(1.-cdp))+X[2]*sdp*ca
    yc=X[0]*ca*sa*(1.-cdp)+X[1]*(ca*ca+sa*sa*cdp)-X[2]*sa*sdp
    zc=X[0]*ca*sdp-X[1]*sdp*sa-X[2]*cdp
# convert back to direction:
    Dir=cart2dir([xc,yc,-zc])
    return Dir[0],Dir[1] # return declination, inclination of rotated direction

def dotilt_V(input):
    """
    does a tilt correction on dec,inc using bedding dip direction bed_az and dip bed_dip
    """
    input=input.transpose()
    dec, inc, bed_az, bed_dip =input[0],input[1],input[2],input[3]  # unpack input array into separate arrays
    rad=numpy.pi/180. # convert to radians
    Dir=numpy.array([dec,inc]).transpose()
    X=dir2cart(Dir).transpose() # get cartesian coordinates
    N=numpy.size(dec)

# get some sines and cosines of new coordinate system
    sa,ca= -numpy.sin(bed_az*rad),numpy.cos(bed_az*rad)
    cdp,sdp= numpy.cos(bed_dip*rad),numpy.sin(bed_dip*rad)
# do the rotation
    xc=X[0]*(sa*sa+ca*ca*cdp)+X[1]*(ca*sa*(1.-cdp))+X[2]*sdp*ca
    yc=X[0]*ca*sa*(1.-cdp)+X[1]*(ca*ca+sa*sa*cdp)-X[2]*sa*sdp
    zc=X[0]*ca*sdp-X[1]*sdp*sa-X[2]*cdp
# convert back to direction:
    cart=numpy.array([xc,yc,-zc]).transpose()
    Dir=cart2dir(cart).transpose()
    return Dir[0],Dir[1] # return declination, inclination arrays of rotated direction

def dogeo(dec,inc,az,pl):
    """
    called as:  dogeo(dec,inc,az,pl)
    rotates dec,inc into geographic coordinates using az,pl as azimuth and plunge of X direction
    """
    A1,A2,A3=[],[],[] # set up lists for rotation vector
    Dir=[dec,inc,1.] # put dec inc in direction list and set  length to unity
    X=dir2cart(Dir) # get cartesian coordinates
#
#   set up rotation matrix
#
    A1=dir2cart([az,pl,1.])
    A2=dir2cart([az+90.,0,1.])
    A3=dir2cart([az-180.,90.-pl,1.])
#
# do rotation
#
    xp=A1[0]*X[0]+A2[0]*X[1]+A3[0]*X[2]
    yp=A1[1]*X[0]+A2[1]*X[1]+A3[1]*X[2]
    zp=A1[2]*X[0]+A2[2]*X[1]+A3[2]*X[2]
#
# transform back to dec,inc
#
    Dir_geo=cart2dir([xp,yp,zp])
    return Dir_geo[0],Dir_geo[1]    # send back declination and inclination

def dogeo_V(input):
    """
    rotates dec,in into geographic coordinates using az,pl as azimuth and plunge of X direction
    handles  array for  input
    """
    input=input.transpose()
    dec, inc, az, pl =input[0],input[1],input[2],input[3]  # unpack input array into separate arrays
    Dir=numpy.array([dec,inc]).transpose()
    X=dir2cart(Dir).transpose() # get cartesian coordinates
    N=numpy.size(dec)
    A1=dir2cart(numpy.array([az,pl,numpy.ones(N)]).transpose()).transpose()
    A2=dir2cart(numpy.array([az+90.,numpy.zeros(N),numpy.ones(N)]).transpose()).transpose()
    A3=dir2cart(numpy.array([az-180.,90.-pl,numpy.ones(N)]).transpose()).transpose()

# do rotation
#
    xp=A1[0]*X[0]+A2[0]*X[1]+A3[0]*X[2]
    yp=A1[1]*X[0]+A2[1]*X[1]+A3[1]*X[2]
    zp=A1[2]*X[0]+A2[2]*X[1]+A3[2]*X[2]
    cart=numpy.array([xp,yp,zp]).transpose()
#
# transform back to dec,inc
#
    Dir_geo=cart2dir(cart).transpose()
    return Dir_geo[0],Dir_geo[1]    # send back declination and inclination arrays

def dodirot(D,I,Dbar,Ibar):
    """
    This function is called by dodirot(D,I,Dbar,Ibar) where D=declination, I = inclination and Dbar/Ibar are the desired mean direction.  It returns the rotated Dec/Inc pair.
    """
    d,irot=dogeo(D,I,Dbar,90.-Ibar)
    drot=d-180.
#    drot,irot=dogeo(D,I,Dbar,Ibar)
    if drot<360.:drot=drot+360.
    if drot>360.:drot=drot-360.
    return drot,irot

def find_samp_rec(s,data,az_type):
    """
    find the orientation info for samp s
    """
    datablock,or_error,bed_error=[],0,0
    orient={}
    orient["sample_dip"]=""
    orient["sample_azimuth"]=""
    orient['sample_description']=""
    for rec in data:
        if rec["er_sample_name"].lower()==s.lower():
           if 'sample_orientation_flag' in  rec.keys() and rec['sample_orientation_flag']=='b':
               orient['sample_orientation_flag']='b'
               return orient
           if "magic_method_codes" in rec.keys() and az_type != "0":
               methods=rec["magic_method_codes"].replace(" ","").split(":")
               if az_type in methods and "sample_azimuth" in rec.keys() and rec["sample_azimuth"]!="": orient["sample_azimuth"]= float(rec["sample_azimuth"])
               if "sample_dip" in rec.keys() and rec["sample_dip"]!="": orient["sample_dip"]=float(rec["sample_dip"])
               if "sample_bed_dip_direction" in rec.keys() and rec["sample_bed_dip_direction"]!="":orient["sample_bed_dip_direction"]=float(rec["sample_bed_dip_direction"])
               if "sample_bed_dip" in rec.keys() and rec["sample_bed_dip"]!="":orient["sample_bed_dip"]=float(rec["sample_bed_dip"])
           else:
               if "sample_azimuth" in rec.keys():orient["sample_azimuth"]=float(rec["sample_azimuth"])
               if "sample_dip" in rec.keys(): orient["sample_dip"]=float(rec["sample_dip"])
               if "sample_bed_dip_direction" in rec.keys(): orient["sample_bed_dip_direction"]=float(rec["sample_bed_dip_direction"])
               if "sample_bed_dip" in rec.keys(): orient["sample_bed_dip"]=float(rec["sample_bed_dip"])
               if 'sample_description' in rec.keys(): orient['sample_description']=rec['sample_description']
        if orient["sample_azimuth"]!="": break
    return orient

def vspec(data):
    """
    takes the vector mean of replicate measurements at a give step
    """
    vdata,Dirdata,step_meth=[],[],[]
    tr0=data[0][0] # set beginning treatment
    data.append("Stop")
    k,R=1,0
    for i in range(k,len(data)):
        Dirdata=[]
        if data[i][0] != tr0:
            if i==k: # sample is unique
                vdata.append(data[i-1])
                step_meth.append(" ")
            else: # sample is not unique
                for l in range(k-1,i):
                    Dirdata.append([data[l][1],data[l][2],data[l][3]])
                dir,R=vector_mean(Dirdata)
                vdata.append([data[i-1][0],dir[0],dir[1],R/(i-k+1),'1','g'])
                step_meth.append("DE-VM")
            tr0=data[i][0]
            k=i+1
            if tr0=="stop":break
    del data[-1]
    return step_meth,vdata

def Vdiff(D1,D2):
    """
    finds the vector difference between two directions D1,D2
    """
    A=dir2cart([D1[0],D1[1],1.])
    B=dir2cart([D2[0],D2[1],1.])
    C=[]
    for i in range(3):
        C.append(A[i]-B[i])
    return cart2dir(C)

def angle(D1,D2):
    """
    call to angle(D1,D2) returns array of angles between lists of two directions D1,D2 where D1 is for example, [[Dec1,Inc1],[Dec2,Inc2],etc.]
    """
    D1=numpy.array(D1)
    if len(D1.shape)>1:
        D1=D1[:,0:2] # strip off intensity
    else: D1=D1[:2]
    D2=numpy.array(D2)
    if len(D2.shape)>1:
        D2=D2[:,0:2] # strip off intensity
    else: D2=D2[:2]
    X1=dir2cart(D1) # convert to cartesian from polar
    X2=dir2cart(D2)
    angles=[] # set up a list for angles
    for k in range(X1.shape[0]): # single vector
        angle= numpy.arccos(numpy.dot(X1[k],X2[k]))*180./numpy.pi # take the dot product
        angle=angle%360.
        angles.append(angle)
    return numpy.array(angles)

def cart2dir(cart):
    """
    converts a direction to cartesian coordinates.  takes an array of [x,y,z])
    """
    cart=numpy.array(cart)
    rad=numpy.pi/180. # constant to convert degrees to radians
    if len(cart.shape)>1:
        Xs,Ys,Zs=cart[:,0],cart[:,1],cart[:,2]
    else: #single vector
        Xs,Ys,Zs=cart[0],cart[1],cart[2]
    Rs=numpy.sqrt(Xs**2+Ys**2+Zs**2) # calculate resultant vector length
    Decs=(numpy.arctan2(Ys,Xs)/rad)%360. # calculate declination taking care of correct quadrants (arctan2) and making modulo 360.
    try:
        Incs=numpy.arcsin(Zs/Rs)/rad # calculate inclination (converting to degrees) #
    except:
        print 'trouble in cart2dir' # most likely division by zero somewhere
        return numpy.zeros(3)

    return numpy.array([Decs,Incs,Rs]).transpose() # return the directions list

#def cart2dir(cart): # OLD ONE
#    """
#    converts a direction to cartesian coordinates
#    """
#    Dir=[] # establish a list to put directions in
#    rad=numpy.pi/180. # constant to convert degrees to radians
#    R=numpy.sqrt(cart[0]**2+cart[1]**2+cart[2]**2) # calculate resultant vector length
#    if R==0:
#       print 'trouble in cart2dir'
#       print cart
#       return [0.0,0.0,0.0]
#    D=numpy.arctan2(cart[1],cart[0])/rad  # calculate declination taking care of correct quadrants (arctan2)
#    if D<0:D=D+360. # put declination between 0 and 360.
#    if D>360.:D=D-360.
#    Dir.append(D)  # append declination to Dir list
#    I=numpy.arcsin(cart[2]/R)/rad # calculate inclination (converting to degrees)
#    Dir.append(I) # append inclination to Dir list
#    Dir.append(R) # append vector length to Dir list
#    return Dir # return the directions list

def tauV(T):
    """
    gets the eigenvalues (tau) and eigenvectors (V) from matrix T
    """
    t,V,tr=[],[],0.
    ind1,ind2,ind3=0,1,2
    evalues,evectmps=numpy.linalg.eig(T)
    evectors=numpy.transpose(evectmps)  # to make compatible with Numeric convention
    for tau in evalues:
        tr+=tau
    if tr!=0:
        for i in range(3):
            evalues[i]=evalues[i]/tr
    else:
        return t,V
# sort evalues,evectors
    t1,t2,t3=0.,0.,1.
    for k in range(3):
        if evalues[k] > t1:
            t1,ind1=evalues[k],k
        if evalues[k] < t3:
            t3,ind3=evalues[k],k
    for k in range(3):
        if evalues[k] != t1 and evalues[k] != t3:
            t2,ind2=evalues[k],k
    V.append(evectors[ind1])
    V.append(evectors[ind2])
    V.append(evectors[ind3])
    t.append(t1)
    t.append(t2)
    t.append(t3)
    return t,V

def Tmatrix(X):
    """
    gets the orientation matrix (T) from data in X
    """
    T=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
    for row in X:
        for k in range(3):
            for l in range(3):
                T[k][l] += row[k]*row[l]
    return T

def dir2cart(d):
   # converts list or array of vector directions, in degrees, to array of cartesian coordinates, in x,y,z
    ints=numpy.ones(len(d)).transpose() # get an array of ones to plug into dec,inc pairs
    d=numpy.array(d)
    rad=numpy.pi/180.
    if len(d.shape)>1: # array of vectors
        decs,incs=d[:,0]*rad,d[:,1]*rad
        if d.shape[1]==3: ints=d[:,2] # take the given lengths
    else: # single vector
        decs,incs=numpy.array(d[0])*rad,numpy.array(d[1])*rad
        if len(d)==3:
            ints=numpy.array(d[2])
        else:
            ints=numpy.array([1.])
    cart= numpy.array([ints*numpy.cos(decs)*numpy.cos(incs),ints*numpy.sin(decs)*numpy.cos(incs),ints*numpy.sin(incs)]).transpose()
    return cart

def dms2dd(d):
   # converts list or array of degree, minute, second locations to array of decimal degrees
    d=numpy.array(d)
    if len(d.shape)>1: # array of angles
        degs,mins,secs=d[:,0],d[:,1],d[:,2]
        print degs,mins,secs
    else: # single vector
        degs,mins,secs=numpy.array(d[0]),numpy.array(d[1]),numpy.array(d[2])
        print degs,mins,secs
    dd= numpy.array(degs+mins/60.+secs/3600.).transpose()
    return dd

def findrec(s,data):
    """
    finds all the records belonging to s in data
    """
    datablock=[]
    for rec in data:
       if s==rec[0]:
           datablock.append([rec[1],rec[2],rec[3],rec[4]])
    return datablock

def domean(indata,start,end,calculation_type):
    """
     gets average direction using fisher or pca (line or plane) methods
    """
    mpars={}
    datablock=[]
    start0,end0=start,end
    for ind,rec in enumerate(indata):
        if len(rec)<6:rec.append('g')
        if rec[5]=='b' and ind==start0:
            mpars["specimen_direction_type"]="Error"
            print "Can't select 'bad' point as start for PCA"
            return mpars
        if rec[5]=='b' and ind<start:
            start-=1
            end-=1
        if rec[5]=='b' and ind>start and ind<=end+1:
            end-=1
        if rec[5]=='g':
            datablock.append(rec) # use only good data
    mpars["calculation_type"]=calculation_type
    rad=numpy.pi/180.
    if end>len(datablock)-1 or end<start : end=len(datablock)-1
    control,data,X,Nrec=[],[],[],float(end-start+1)
    cm=[0.,0.,0.]
#
#  get cartesian coordinates
#
    fdata=[]
    for k in range(start,end+1):
        if calculation_type == 'DE-BFL' or calculation_type=='DE-BFL-A' or calculation_type=='DE-BFL-O' :  # best-fit line
            data=[datablock[k][1],datablock[k][2],datablock[k][3]]
        else:
            data=[datablock[k][1],datablock[k][2],1.0] # unit weight
        fdata.append(data)
        cart= dir2cart(data)
        X.append(cart)
    if calculation_type=='DE-BFL-O': # include origin as point
        X.append([0.,0.,0.])
        #pass
    if calculation_type=='DE-FM': # for fisher means
        fpars=fisher_mean(fdata)
        mpars["specimen_direction_type"]='l'
        mpars["specimen_dec"]=fpars["dec"]
        mpars["specimen_inc"]=fpars["inc"]
        mpars["specimen_alpha95"]=fpars["alpha95"]
        mpars["specimen_n"]=fpars["n"]
        mpars["specimen_r"]=fpars["r"]
        mpars["measurement_step_min"]=indata[start0][0]
        mpars["measurement_step_max"]=indata[end0][0]
        mpars["center_of_mass"]=cm
        mpars["specimen_dang"]=-1
        return mpars
#
#	get center of mass for principal components (DE-BFL or DE-BFP)
#
    for cart in X:
        for l in range(3):
            cm[l]+=cart[l]/Nrec
    mpars["center_of_mass"]=cm

#
#   transform to center of mass (if best-fit line)
#
    if calculation_type!='DE-BFP': mpars["specimen_direction_type"]='l'
    if calculation_type=='DE-BFL' or calculation_type=='DE-BFL-O': # not for planes or anchored lines
        for k in range(len(X)):
            for l in range(3):
               X[k][l]=X[k][l]-cm[l]
    else:
        mpars["specimen_direction_type"]='p'
#
#   put in T matrix
#
    T=numpy.array(Tmatrix(X))
#
#   get sorted evals/evects
#
    t,V=tauV(T)
    if t[2]<0:t[2]=0 # make positive
    if t==[]:
        mpars["specimen_direction_type"]="Error"
        print "Error in calculation"
        return mpars
    v1,v3=V[0],V[2]
    if calculation_type=='DE-BFL-A':
        Dir,R=vector_mean(fdata)
        mpars["specimen_direction_type"]='l'
        mpars["specimen_dec"]=Dir[0]
        mpars["specimen_inc"]=Dir[1]
        mpars["specimen_n"]=len(fdata)
        mpars["measurement_step_min"]=indata[start0][0]
        mpars["measurement_step_max"]=indata[end0][0]
        mpars["center_of_mass"]=cm
        s1=numpy.sqrt(t[0])
        MAD=numpy.arctan(numpy.sqrt(t[1]+t[2])/s1)/rad
        mpars["specimen_mad"]=MAD # I think this is how it is done - i never anchor the "PCA" - check
        return mpars
    if calculation_type!='DE-BFP':
#
#   get control vector for principal component direction
#
        rec=[datablock[start][1],datablock[start][2],datablock[start][3]]
        P1=dir2cart(rec)
        rec=[datablock[end][1],datablock[end][2],datablock[end][3]]
        P2=dir2cart(rec)
#
#   get right direction along principal component
##
        for k in range(3):
            control.append(P1[k]-P2[k])
        # changed by rshaar
        # control is taken as the center of mass
        #control=cm


        dot = 0
        for k in range(3):
            dot += v1[k]*control[k]
        if dot<-1:dot=-1
        if dot>1:dot=1
        if numpy.arccos(dot) > numpy.pi/2.:
            for k in range(3):
                v1[k]=-v1[k]
#   get right direction along principal component
#
        s1=numpy.sqrt(t[0])
        Dir=cart2dir(v1)
        MAD=numpy.arctan(numpy.sqrt(t[1]+t[2])/s1)/rad
    if calculation_type=="DE-BFP":
        Dir=cart2dir(v3)
        MAD=numpy.arctan(numpy.sqrt(t[2]/t[1]+t[2]/t[0]))/rad
#
#  	get angle with  center of mass
#
    CMdir=cart2dir(cm)
    Dirp=[Dir[0],Dir[1],1.]
    dang=angle(CMdir,Dirp)
    mpars["specimen_dec"]=Dir[0]
    mpars["specimen_inc"]=Dir[1]
    mpars["specimen_mad"]=MAD
    #mpars["specimen_n"]=int(Nrec)
    mpars["specimen_n"]=len(X)
    mpars["specimen_dang"]=dang[0]
    mpars["measurement_step_min"]=indata[start0][0]
    mpars["measurement_step_max"]=indata[end0][0]
    return mpars

def circ(dec,dip,alpha):
    """
    function to calculate points on an circle about dec,dip with angle alpha
    """
    rad=numpy.pi/180.
    D_out,I_out=[],[]
    dec,dip,alpha=dec*rad ,dip*rad,alpha*rad
    dec1=dec+numpy.pi/2.
    isign=1
    if dip!=0: isign=(abs(dip)/dip)
    dip1=(dip-isign*(numpy.pi/2.))
    t=[[0,0,0],[0,0,0],[0,0,0]]
    v=[0,0,0]
    t[0][2]=numpy.cos(dec)*numpy.cos(dip)
    t[1][2]=numpy.sin(dec)*numpy.cos(dip)
    t[2][2]=numpy.sin(dip)
    t[0][1]=numpy.cos(dec)*numpy.cos(dip1)
    t[1][1]=numpy.sin(dec)*numpy.cos(dip1)
    t[2][1]=numpy.sin(dip1)
    t[0][0]=numpy.cos(dec1)
    t[1][0]=numpy.sin(dec1)
    t[2][0]=0
    for i in range(101):
        psi=float(i)*numpy.pi/50.
        v[0]=numpy.sin(alpha)*numpy.cos(psi)
        v[1]=numpy.sin(alpha)*numpy.sin(psi)
        v[2]=numpy.sqrt(abs(1.-v[0]**2 - v[1]**2))
        elli=[0,0,0]
        for j in range(3):
            for k in range(3):
                elli[j]=elli[j] + t[j][k]*v[k]
        Dir=cart2dir(elli)
        D_out.append(Dir[0])
        I_out.append(Dir[1])
    return D_out,I_out

def PintPars(datablock,araiblock,zijdblock,start,end,accept):
    """
     calculate the paleointensity magic parameters  make some definitions
    """
    methcode,ThetaChecks,DeltaChecks,GammaChecks="","","",""
    zptrm_check=[]
    first_Z,first_I,ptrm_check,ptrm_tail,zptrm_check,GammaChecks=araiblock[0],araiblock[1],araiblock[2],araiblock[3],araiblock[4],araiblock[5]
    if len(araiblock)>6:
        ThetaChecks=araiblock[6] # used only for perpendicular method of paleointensity
        DeltaChecks=araiblock[7] # used only for perpendicular  method of paleointensity
    xi,yi,diffcum=[],[],0
    xiz,xzi,yiz,yzi=[],[],[],[]
    Nptrm,dmax=0,-1e-22
# check if even zero and infield steps
    if len(first_Z)>len(first_I):
        maxe=len(first_I)-1
    else: maxe=len(first_Z)-1
    if end==0 or end > maxe:
        end=maxe
# get the MAD, DANG, etc. for directional data
    bstep=araiblock[0][start][0]
    estep=araiblock[0][end][0]
    zstart,zend=0,len(zijdblock)
    for k in range(len(zijdblock)):
        zrec=zijdblock[k]
        if zrec[0]==bstep:zstart=k
        if zrec[0]==estep:zend=k
    PCA=domean(zijdblock,zstart,zend,'DE-BFL')
    D,Diz,Dzi,Du=[],[],[],[]  # list of NRM vectors, and separated by zi and iz
    for rec in zijdblock:
        D.append((rec[1],rec[2],rec[3]))
        Du.append((rec[1],rec[2]))
        if rec[4]==1:
            Dzi.append((rec[1],rec[2]))  # if this is ZI step
        else:
            Diz.append((rec[1],rec[2]))  # if this is IZ step
# calculate the vector difference sum
    vds=dovds(D)
    b_zi,b_iz=[],[]
# collect data included in ZigZag calculation
    if end+1>=len(first_Z):
        stop=end-1
    else:
        stop=end
    for k in range(start,end+1):
       for l in range(len(first_I)):
           irec=first_I[l]
           if irec[0]==first_Z[k][0]:
               xi.append(irec[3])
               yi.append(first_Z[k][3])
    pars,errcode=int_pars(xi,yi,vds)
    if errcode==1:return pars,errcode
#    for k in range(start,end+1):
    for k in range(len(first_Z)-1):
        for l in range(k):
            if first_Z[k][3]/vds>0.1:   # only go down to 10% of NRM.....
               irec=first_I[l]
               if irec[4]==1 and first_I[l+1][4]==0: # a ZI step
                   xzi=irec[3]
                   yzi=first_Z[k][3]
                   xiz=first_I[l+1][3]
                   yiz=first_Z[k+1][3]
                   slope=numpy.arctan2((yzi-yiz),(xiz-xzi))
                   r=numpy.sqrt( (yzi-yiz)**2+(xiz-xzi)**2)
                   if r>.1*vds:b_zi.append(slope) # suppress noise
               elif irec[4]==0 and first_I[l+1][4]==1: # an IZ step
                   xiz=irec[3]
                   yiz=first_Z[k][3]
                   xzi=first_I[l+1][3]
                   yzi=first_Z[k+1][3]
                   slope=numpy.arctan2((yiz-yzi),(xzi-xiz))
                   r=numpy.sqrt( (yiz-yzi)**2+(xzi-xiz)**2)
                   if r>.1*vds:b_iz.append(slope) # suppress noise
#
    ZigZag,Frat,Trat=-1,0,0
    if len(Diz)>2 and len(Dzi)>2:
        ZigZag=0
        dizp=fisher_mean(Diz) # get Fisher stats on IZ steps
        dzip=fisher_mean(Dzi) # get Fisher stats on ZI steps
        dup=fisher_mean(Du) # get Fisher stats on all steps
#
# if directions are TOO well grouped, can get false positive for ftest, so
# angles must be > 3 degrees apart.
#
        if angle([dizp['dec'],dizp['inc']],[dzip['dec'],dzip['inc']])>3.:
            F=(dup['n']-2.)* (dzip['r']+dizp['r']-dup['r'])/(dup['n']-dzip['r']-dizp['r']) # Watson test for common mean
            nf=2.*(dup['n']-2.) # number of degees of freedom
            ftest=fcalc(2,nf)
            Frat=F/ftest
            if Frat>1.:
                ZigZag=Frat # fails zigzag on directions
                methcode="SM-FTEST"
# now do slopes
    if len(b_zi)>2 and len(b_iz)>2:
        bzi_m,bzi_sig=gausspars(b_zi)  # mean, std dev
        biz_m,biz_sig=gausspars(b_iz)
        n_zi=float(len(b_zi))
        n_iz=float(len(b_iz))
        b_diff=abs(bzi_m-biz_m) # difference in means
#
# avoid false positives - set 3 degree slope difference here too
        if b_diff>3*numpy.pi/180.:
            nf=n_zi+n_iz-2.  # degrees of freedom
            svar= ((n_zi-1.)*bzi_sig**2 + (n_iz-1.)*biz_sig**2)/nf
            T=(b_diff)/numpy.sqrt(svar*(1.0/n_zi + 1.0/n_iz)) # student's t
            ttest=tcalc(nf,.05) # t-test at 95% conf.
            Trat=T/ttest
            if Trat>1  and Trat>Frat:
                ZigZag=Trat # fails zigzag on directions
                methcode="SM-TTEST"
    pars["specimen_Z"]=ZigZag
    pars["method_codes"]=methcode
# do drats
    if len(ptrm_check) != 0:
        diffcum,drat_max=0,0
        for prec in ptrm_check:
            step=prec[0]
            endbak=end
            zend=end
            while zend>len(zijdblock)-1:
               zend=zend-2  # don't count alteration that happens after this step
            if step <zijdblock[zend][0]:
                Nptrm+=1
                for irec in first_I:
                    if irec[0]==step:break
                diffcum+=prec[3]-irec[3]
                if abs(prec[3]-irec[3])>drat_max:drat_max=abs(prec[3]-irec[3])
        pars["specimen_drats"]=(100*abs(diffcum)/first_I[zend][3])
        pars["specimen_drat"]=(100*abs(drat_max)/first_I[zend][3])
    elif len(zptrm_check) != 0:
        diffcum=0
        for prec in zptrm_check:
            step=prec[0]
            endbak=end
            zend=end
            while zend>len(zijdblock)-1:
               zend=zend-1
            if step <zijdblock[zend][0]:
                Nptrm+=1
                for irec in first_I:
                    if irec[0]==step:break
                diffcum+=prec[3]-irec[3]
        pars["specimen_drats"]=(100*abs(diffcum)/first_I[zend][3])
    else:
        pars["specimen_drats"]=-1
        pars["specimen_drat"]=-1
# and the pTRM tails
    if len(ptrm_tail) != 0:
        for trec in ptrm_tail:
            step=trec[0]
            for irec in first_I:
                if irec[0]==step:break
            if abs(trec[3]) >dmax:dmax=abs(trec[3])
        pars["specimen_md"]=(100*dmax/vds)
    else: pars["specimen_md"]=-1
    pars["measurement_step_min"]=bstep
    pars["measurement_step_max"]=estep
    pars["specimen_dec"]=PCA["specimen_dec"]
    pars["specimen_inc"]=PCA["specimen_inc"]
    pars["specimen_int_mad"]=PCA["specimen_mad"]
    pars["specimen_int_dang"]=PCA["specimen_dang"]
    #pars["specimen_int_ptrm_n"]=len(ptrm_check) # this is WRONG!
    pars["specimen_int_ptrm_n"]=Nptrm
# and the ThetaChecks
    if ThetaChecks!="":
        t=0
        for theta in ThetaChecks:
            if theta[0]>=bstep and theta[0]<=estep and theta[1]>t:t=theta[1]
        pars['specimen_theta']=t
    else:
        pars['specimen_theta']=-1
# and the DeltaChecks
    if DeltaChecks!="":
        d=0
        for delta in DeltaChecks:
            if delta[0]>=bstep and delta[0]<=estep and delta[1]>d:d=delta[1]
        pars['specimen_delta']=d
    else:
        pars['specimen_delta']=-1
    pars['specimen_gamma']=-1
    if GammaChecks!="":
        for gamma in GammaChecks:
            if gamma[0]<=estep: pars['specimen_gamma']=gamma[1]


    #--------------------------------------------------------------
    # From here added By Ron Shaar 11-Dec 2012
    # New parameters defined in Shaar and Tauxe (2012):
    # FRAC (specimen_frac) - ranges from 0. to 1.
    # SCAT (specimen_scat) - takes 1/0
    # gap_max (specimen_gmax) - ranges from 0. to 1.
    #--------------------------------------------------------------

    #--------------------------------------------------------------
    # FRAC is similar to Fvds, but the numerator is the vds fraction:
    # FRAC= [ vds (start,end)] / total vds ]
    # gap_max= max [ (vector difference) /  vds (start,end)]
    #--------------------------------------------------------------

    # collect all zijderveld data to arrays and calculate VDS

    z_temperatures=[row[0] for row in zijdblock]
    zdata=[]                # array of zero-fields measurements in Cartezian coordinates
    vector_diffs=[]         # array of vector differences (for vds calculation)
    NRM=zijdblock[0][3]     # NRM

    for k in range(len(zijdblock)):
        DIR=[zijdblock[k][1],zijdblock[k][2],zijdblock[k][3]/NRM]
        cart=dir2cart(DIR)
        zdata.append(array([cart[0],cart[1],cart[2]]))
        if k>0:
            vector_diffs.append(sqrt(sum((array(zdata[-2])-array(zdata[-1]))**2)))
    vector_diffs.append(sqrt(sum(array(zdata[-1])**2))) # last vector differnce: from the last point to the origin.
    vds=sum(vector_diffs)  # vds calculation
    zdata=array(zdata)
    vector_diffs=array(vector_diffs)

    # calculate the vds within the chosen segment
    vector_diffs_segment=vector_diffs[zstart:zend]
    # FRAC calculation
    FRAC=sum(vector_diffs_segment)/vds
    pars['specimen_frac']=FRAC

    # gap_max calculation
    max_FRAC_gap=max(vector_diffs_segment/sum(vector_diffs_segment))
    pars['specimen_gmax']=max_FRAC_gap


    #---------------------------------------------------------------------
    # Calculate the "scat box"
    # all data-points, pTRM checks, and tail-checks, should be inside a "scat box"
    #---------------------------------------------------------------------

    # intialization
    pars["fail_arai_beta_box_scatter"]=False # fail scat due to arai plot data points
    pars["fail_ptrm_beta_box_scatter"]=False # fail scat due to pTRM checks
    pars["fail_tail_beta_box_scatter"]=False # fail scat due to tail checks
    pars["specimen_scat"]="1" # Pass by default

    #--------------------------------------------------------------
    # collect all Arai plot data points in arrays

    x_Arai,y_Arai,t_Arai,steps_Arai=[],[],[],[]
    NRMs=araiblock[0]
    PTRMs=araiblock[1]
    ptrm_checks = araiblock[2]
    ptrm_tail = araiblock[3]

    PTRMs_temperatures=[row[0] for row in PTRMs]
    NRMs_temperatures=[row[0] for row in NRMs]
    NRM=NRMs[0][3]

    for k in range(len(NRMs)):
      index_pTRMs=PTRMs_temperatures.index(NRMs[k][0])
      x_Arai.append(PTRMs[index_pTRMs][3]/NRM)
      y_Arai.append(NRMs[k][3]/NRM)
      t_Arai.append(NRMs[k][0])
      if NRMs[k][4]==1:
        steps_Arai.append('ZI')
      else:
        steps_Arai.append('IZ')
    x_Arai=array(x_Arai)
    y_Arai=array(y_Arai)

    #--------------------------------------------------------------
    # collect all pTRM check to arrays

    x_ptrm_check,y_ptrm_check,ptrm_checks_temperatures,=[],[],[]
    x_ptrm_check_starting_point,y_ptrm_check_starting_point,ptrm_checks_starting_temperatures=[],[],[]

    for k in range(len(ptrm_checks)):
      if ptrm_checks[k][0] in NRMs_temperatures:
        # find the starting point of the pTRM check:
        for i in range(len(datablock)):
            rec=datablock[i]
            if "LT-PTRM-I" in rec['magic_method_codes'] and float(rec['treatment_temp'])==ptrm_checks[k][0]:
                starting_temperature=(float(datablock[i-1]['treatment_temp']))
                try:
                    index=t_Arai.index(starting_temperature)
                    x_ptrm_check_starting_point.append(x_Arai[index])
                    y_ptrm_check_starting_point.append(y_Arai[index])
                    ptrm_checks_starting_temperatures.append(starting_temperature)

                    index_zerofield=zerofield_temperatures.index(ptrm_checks[k][0])
                    x_ptrm_check.append(ptrm_checks[k][3]/NRM)
                    y_ptrm_check.append(zerofields[index_zerofield][3]/NRM)
                    ptrm_checks_temperatures.append(ptrm_checks[k][0])

                    break
                except:
                    pass

    x_ptrm_check_starting_point=array(x_ptrm_check_starting_point)
    y_ptrm_check_starting_point=array(y_ptrm_check_starting_point)
    ptrm_checks_starting_temperatures=array(ptrm_checks_starting_temperatures)
    x_ptrm_check=array(x_ptrm_check)
    y_ptrm_check=array(y_ptrm_check)
    ptrm_checks_temperatures=array(ptrm_checks_temperatures)

    #--------------------------------------------------------------
    # collect tail checks to arrays

    x_tail_check,y_tail_check,tail_check_temperatures=[],[],[]
    x_tail_check_starting_point,y_tail_check_starting_point,tail_checks_starting_temperatures=[],[],[]

    for k in range(len(ptrm_tail)):
      if ptrm_tail[k][0] in NRMs_temperatures:

        # find the starting point of the pTRM check:
        for i in range(len(datablock)):
            rec=datablock[i]
            if "LT-PTRM-MD" in rec['magic_method_codes'] and float(rec['treatment_temp'])==ptrm_tail[k][0]:
                starting_temperature=(float(datablock[i-1]['treatment_temp']))
                try:

                    index=t_Arai.index(starting_temperature)
                    x_tail_check_starting_point.append(x_Arai[index])
                    y_tail_check_starting_point.append(y_Arai[index])
                    tail_checks_starting_temperatures.append(starting_temperature)

                    index_infield=infield_temperatures.index(ptrm_tail[k][0])
                    x_tail_check.append(infields[index_infield][3]/NRM)
                    y_tail_check.append(ptrm_tail[k][3]/NRM + zerofields[index_infield][3]/NRM)
                    tail_check_temperatures.append(ptrm_tail[k][0])

                    break
                except:
                    pass

    x_tail_check=array(x_tail_check)
    y_tail_check=array(y_tail_check)
    tail_check_temperatures=array(tail_check_temperatures)
    x_tail_check_starting_point=array(x_tail_check_starting_point)
    y_tail_check_starting_point=array(y_tail_check_starting_point)
    tail_checks_starting_temperatures=array(tail_checks_starting_temperatures)


    #--------------------------------------------------------------
    # collect the chosen segment in the Arai plot to arraya

    x_Arai_segment= x_Arai[start:end+1] # chosen segent in the Arai plot
    y_Arai_segment= y_Arai[start:end+1] # chosen segent in the Arai plot

    #--------------------------------------------------------------
    # collect pTRM checks in segment to arrays
    # notice, this is different than the conventional DRATS.
    # for scat calculation we take only the pTRM checks which were carried out
    # before reaching the highest temperature in the chosen segment

    x_ptrm_check_for_SCAT,y_ptrm_check_for_SCAT=[],[]
    for k in range(len(ptrm_checks_temperatures)):
      if ptrm_checks_temperatures[k] >= pars["measurement_step_min"] and ptrm_checks_starting_temperatures <= pars["measurement_step_max"] :
            x_ptrm_check_for_SCAT.append(x_ptrm_check[k])
            y_ptrm_check_for_SCAT.append(y_ptrm_check[k])

    x_ptrm_check_for_SCAT=array(x_ptrm_check_for_SCAT)
    y_ptrm_check_for_SCAT=array(y_ptrm_check_for_SCAT)

    #--------------------------------------------------------------
    # collect Tail checks in segment to arrays
    # for scat calculation we take only the tail checks which were carried out
    # before reaching the highest temperature in the chosen segment

    x_tail_check_for_SCAT,y_tail_check_for_SCAT=[],[]

    for k in range(len(tail_check_temperatures)):
      if tail_check_temperatures[k] >= pars["measurement_step_min"] and tail_checks_starting_temperatures[k] <= pars["measurement_step_max"] :
            x_tail_check_for_SCAT.append(x_tail_check[k])
            y_tail_check_for_SCAT.append(y_tail_check[k])


    x_tail_check_for_SCAT=array(x_tail_check_for_SCAT)
    y_tail_check_for_SCAT=array(y_tail_check_for_SCAT)

    #--------------------------------------------------------------
    # calculate the lines that define the scat box:

    # if threshold value for beta is not defined, then scat cannot be calculated (pass)
    # in this case, scat pass
    if 'specimen_b_beta' in accept.keys() and accept['specimen_b_beta']!="":
        b_beta_threshold=float(accept['specimen_b_beta'])
        b=pars['specimen_b']             # best fit line
        cm_x=mean(array(x_Arai_segment)) # x center of mass
        cm_y=mean(array(y_Arai_segment)) # y center of mass
        a=cm_y-b*cm_x

        # lines with slope = slope +/- 2*(specimen_b_beta)

        two_sigma_beta_threshold=2*b_beta_threshold
        two_sigma_slope_threshold=abs(two_sigma_beta_threshold*b)

        # a line with a  shallower  slope  (b + 2*beta*b) passing through the center of mass
        # y=a1+b1x
        b1=b+two_sigma_slope_threshold
        a1=cm_y-b1*cm_x

        # bounding line with steeper  slope (b - 2*beta*b) passing through the center of mass
        # y=a2+b2x
        b2=b-two_sigma_slope_threshold
        a2=cm_y-b2*cm_x

        # lower bounding line of the 'beta box'
        # y=intercept1+slop1x
        slop1=a1/((a2/b2))
        intercept1=a1

        # higher bounding line of the 'beta box'
        # y=intercept2+slop2x

        slop2=a2/((a1/b1))
        intercept2=a2

        pars['specimen_scat_bounding_line_high']=[intercept2,slop2]
        pars['specimen_scat_bounding_line_low']=[intercept1,slop1]

        #--------------------------------------------------------------
        # check if the Arai data points are in the 'box'

        # the two bounding lines
        ymin=intercept1+x_Arai_segment*slop1
        ymax=intercept2+x_Arai_segment*slop2

        # arrays of "True" or "False"
        check_1=y_Arai_segment>ymax
        check_2=y_Arai_segment<ymin

        # check if at least one "True"
        if (sum(check_1)+sum(check_2))>0:
         pars["fail_arai_beta_box_scatter"]=True

        #--------------------------------------------------------------
        # check if the pTRM checks data points are in the 'box'

        if len(x_ptrm_check_for_SCAT) > 0:

          # the two bounding lines
          ymin=intercept1+x_ptrm_check_for_SCAT*slop1
          ymax=intercept2+x_ptrm_check_for_SCAT*slop2

          # arrays of "True" or "False"
          check_1=y_ptrm_check_for_SCAT>ymax
          check_2=y_ptrm_check_for_SCAT<ymin


          # check if at least one "True"
          if (sum(check_1)+sum(check_2))>0:
            pars["fail_ptrm_beta_box_scatter"]=True

        #--------------------------------------------------------------
        # check if the tail checks data points are in the 'box'


        if len(x_tail_check_for_SCAT) > 0:

          # the two bounding lines
          ymin=intercept1+x_tail_check_for_SCAT*slop1
          ymax=intercept2+x_tail_check_for_SCAT*slop2

          # arrays of "True" or "False"
          check_1=y_tail_check_for_SCAT>ymax
          check_2=y_tail_check_for_SCAT<ymin


          # check if at least one "True"
          if (sum(check_1)+sum(check_2))>0:
            pars["fail_tail_beta_box_scatter"]=True

        #--------------------------------------------------------------
        # check if specimen_scat is PASS or FAIL:

        if pars["fail_tail_beta_box_scatter"] or pars["fail_ptrm_beta_box_scatter"] or pars["fail_arai_beta_box_scatter"]:
              pars["specimen_scat"]='0'
        else:
              pars["specimen_scat"]='1'

    return pars,0

def getkeys(table):
    """
    customize by commenting out unwanted keys
    """
    keys=[]
    if table=="ER_expedition":
        pass
    if table=="ER_citations":
        keys.append("er_citation_name")
        keys.append("long_authors")
        keys.append("year")
        keys.append("title")
        keys.append("citation_type")
        keys.append("doi")
        keys.append("journal")
        keys.append("volume")
        keys.append("pages")
        keys.append("book_title")
        keys.append("book_editors")
        keys.append("publisher")
        keys.append("city")
    if table=="ER_locations":
        keys.append("er_location_name")
        keys.append("er_scientist_mail_names" )
#        keys.append("er_location_alternatives" )
        keys.append("location_type" )
        keys.append("location_begin_lat")
        keys.append("location_begin_lon" )
#        keys.append("location_begin_elevation" )
        keys.append("location_end_lat" )
        keys.append("location_end_lon" )
#        keys.append("location_end_elevation" )
        keys.append("continent_ocean" )
        keys.append("country" )
        keys.append("region" )
        keys.append("plate_block" )
        keys.append("terrane" )
        keys.append("tectonic_setting" )
#        keys.append("er_citation_names")
    if table=="ER_Formations":
        keys.append("er_formation_name")
        keys.append("formation_class")
        keys.append("formation_lithology")
        keys.append("formation_paleo_environment")
        keys.append("formation_thickness")
        keys.append("formation_description")
    if table=="ER_sections":
        keys.append("er_section_name")
        keys.append("er_section_alternatives")
        keys.append("er_expedition_name")
        keys.append("er_location_name")
        keys.append("er_formation_name")
        keys.append("er_member_name")
        keys.append("section_definition")
        keys.append("section_class")
        keys.append("section_lithology")
        keys.append("section_type")
        keys.append("section_n")
        keys.append("section_begin_lat")
        keys.append("section_begin_lon")
        keys.append("section_begin_elevation")
        keys.append("section_begin_height")
        keys.append("section_begin_drill_depth")
        keys.append("section_begin_composite_depth")
        keys.append("section_end_lat")
        keys.append("section_end_lon")
        keys.append("section_end_elevation")
        keys.append("section_end_height")
        keys.append("section_end_drill_depth")
        keys.append("section_end_composite_depth")
        keys.append("section_azimuth")
        keys.append("section_dip")
        keys.append("section_description")
        keys.append("er_scientist_mail_names")
        keys.append("er_citation_names")
    if table=="ER_sites":
        keys.append("er_location_name")
        keys.append("er_site_name")
#        keys.append("er_site_alternatives")
#        keys.append("er_formation_name")
#        keys.append("er_member_name")
#        keys.append("er_section_name")
        keys.append("er_scientist_mail_names")
        keys.append("site_class")
#        keys.append("site_type")
#        keys.append("site_lithology")
#        keys.append("site_height")
#        keys.append("site_drill_depth")
#        keys.append("site_composite_depth")
#        keys.append("site_lithology")
#        keys.append("site_description")
        keys.append("site_lat")
        keys.append("site_lon")
#        keys.append("site_location_precision")
#        keys.append("site_elevation")
    if table == "ER_samples" :
        keys.append("er_location_name")
        keys.append("er_site_name")
#       keys.append("er_sample_alternatives")
        keys.append("sample_azimuth")
        keys.append("sample_dip")
        keys.append("sample_bed_dip")
        keys.append("sample_bed_dip_direction")
#       keys.append("sample_cooling_rate")
#       keys.append("sample_type")
#       keys.append("sample_lat")
#       keys.append("sample_lon")
        keys.append("magic_method_codes")
    if table == "ER_ages" :
#       keys.append("er_location_name")
#       keys.append("er_site_name")
#       keys.append("er_section_name")
#       keys.append("er_formation_name")
#       keys.append("er_member_name")
#       keys.append("er_site_name")
#       keys.append("er_sample_name")
#       keys.append("er_specimen_name")
#       keys.append("er_fossil_name")
#       keys.append("er_mineral_name")
#       keys.append("tiepoint_name")
        keys.append("age")
        keys.append("age_sigma")
        keys.append("age_unit")
        keys.append("age_range_low")
        keys.append("age_range_hi")
        keys.append("timescale_eon")
        keys.append("timescale_era")
        keys.append("timescale_period")
        keys.append("timescale_epoch")
        keys.append("timescale_stage")
        keys.append("biostrat_zone")
        keys.append("conodont_zone")
        keys.append("magnetic_reversal_chron")
        keys.append("astronomical_stage")
#       keys.append("age_description")
#       keys.append("magic_method_codes")
#       keys.append("er_timescale_citation_names")
#       keys.append("er_citation_names")
    if table == "MAGIC_measurements" :
        keys.append("er_location_name")
        keys.append("er_site_name")
        keys.append("er_sample_name")
        keys.append("er_specimen_name")
        keys.append("measurement_positions")
        keys.append("treatment_temp")
        keys.append("treatment_ac_field")
        keys.append("treatment_dc_field")
        keys.append("treatment_dc_field_phi")
        keys.append("treatment_dc_field_theta")
        keys.append("magic_experiment_name")
        keys.append("magic_instrument_codes")
        keys.append("measurement_temp")
        keys.append("magic_method_codes")
        keys.append("measurement_inc")
        keys.append("measurement_dec")
        keys.append("measurement_magn_moment")
        keys.append("measurement_csd")
    return  keys

def getnames():
    """
    get mail names
    """
    namestring=""
    addmore=1
    while addmore:
        scientist=raw_input("Enter  name  - <Return> when done ")
        if scientist != "":
            namestring=namestring+":"+scientist
        else:
            namestring=namestring[1:]
            addmore=0
    return namestring

def magic_help(keyhelp):
    """
    returns a help message for a give magic key
    """
    helpme={}
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_location_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["location_type"]=	"Location type"
    helpme["location_begin_lat"]=	"Begin of section or core or outcrop -- latitude"
    helpme["location_begin_lon"]=	"Begin of section or core or outcrop -- longitude"
    helpme["location_begin_elevation"]=	"Begin of section or core or outcrop -- elevation relative to sealevel"
    helpme["location_end_lat"]=	"Ending of section or core -- latitude "
    helpme["location_end_lon"]=	"Ending of section or core -- longitude "
    helpme["location_end_elevation"]=	"Ending of section or core -- elevation relative to sealevel"
    helpme["location_geoid"]=	"Geoid used in determination of latitude and longitude:  WGS84, GEOID03, USGG2003, GEOID99, G99SSS , G99BM, DEFLEC99 "
    helpme["continent_ocean"]=	"Name for continent or ocean island region"
    helpme["ocean_sea"]=	"Name for location in an ocean or sea"
    helpme["country"]=	"Country name"
    helpme["region"]=	"Region name"
    helpme["plate_block"]=	"Plate or tectonic block name"
    helpme["terrane"]=	"Terrane name"
    helpme["tectonic_setting"]=	"Tectonic setting"
    helpme["location_description"]=	"Detailed description"
    helpme["location_url"]=	"Website URL for the location explicitly"
    helpme["er_scientist_mail_names"]=	"Colon-delimited list of names for scientists who described location"
    helpme["er_citation_names"]=	"Colon-delimited list of citations"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_formation_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["formation_class"]=	"General lithology class: igneous, metamorphic or sedimentary"
    helpme["formation_lithology"]=	"Lithology: e.g., basalt, sandstone, etc."
    helpme["formation_paleo_enviroment"]=	"Depositional environment"
    helpme["formation_thickness"]=	"Formation thickness"
    helpme["er_member_name"]=	"Name for member"
    helpme["er_member_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["member_class"]=	"General lithology type"
    helpme["member_lithology"]=	"Lithology"
    helpme["member_paleo_environment"]=	"Depositional environment"
    helpme["member_thickness"]=	"Member thickness"
    helpme["member_description"]=	"Detailed description"
    helpme["er_section_name"]=	"Name for section or core"
    helpme["er_section_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["er_expedition_name"]=	"Name for seagoing or land expedition"
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_member_name"]=	"Name for member"
    helpme["section_definition"]=	"General definition of section"
    helpme["section_class"]=	"General lithology type"
    helpme["section_lithology"]=	"Section lithology or archeological classification"
    helpme["section_type"]=	"Section type"
    helpme["section_n"]=	"Number of subsections included composite (stacked) section"
    helpme["section_begin_lat"]=	"Begin of section or core -- latitude"
    helpme["section_begin_lon"]=	"Begin of section or core -- longitude"
    helpme["section_begin_elevation"]=	"Begin of section or core -- elevation relative to sealevel"
    helpme["section_begin_height"]=	"Begin of section or core -- stratigraphic height"
    helpme["section_begin_drill_depth"]=	"Begin of section or core -- depth in MBSF as used by ODP"
    helpme["section_begin_composite_depth"]=	"Begin of section or core -- composite depth in MBSF as used by ODP"
    helpme["section_end_lat"]=	"End of section or core -- latitude "
    helpme["section_end_lon"]=	"End of section or core -- longitude "
    helpme["section_end_elevation"]=	"End of section or core -- elevation relative to sealevel"
    helpme["section_end_height"]=	"End of section or core -- stratigraphic height"
    helpme["section_end_drill_depth"]=	"End of section or core -- depth in MBSF as used by ODP"
    helpme["section_end_composite_depth"]=	"End of section or core -- composite depth in MBSF as used by ODP"
    helpme["section_azimuth"]=	"Section azimuth as measured clockwise from the north"
    helpme["section_dip"]=	"Section dip as measured into the outcrop"
    helpme["section_description"]=	"Detailed description"
    helpme["er_site_name"]=	"Name for site"
    helpme["er_site_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["er_expedition_name"]=	"Name for seagoing or land expedition"
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_section_name"]=	"Name for section or core"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_member_name"]=	"Name for member"
    helpme["site_definition"]=	"General definition of site"
    helpme["site_class"]=	"[A]rchaeologic,[E]xtrusive,[I]ntrusive,[M]etamorphic,[S]edimentary"
    helpme["site_lithology"]=	"Site lithology or archeological classification"
    helpme["site_type"]=	"Site type: slag, lava flow, sediment layer, etc."
    helpme["site_lat"]=	"Site location -- latitude"
    helpme["site_lon"]=	"Site location -- longitude"
    helpme["site_location_precision"]=	"Site location -- precision in latitude and longitude"
    helpme["site_elevation"]=	"Site location -- elevation relative to sealevel"
    helpme["site_height"]=	"Site location -- stratigraphic height"
    helpme["site_drill_depth"]=	"Site location -- depth in MBSF as used by ODP"
    helpme["site_composite_depth"]=	"Site location -- composite depth in MBSF as used by ODP"
    helpme["site_description"]=	"Detailed description"
    helpme["magic_method_codes"]=	"Colon-delimited list of method codes"
    helpme["er_sample_name"]=	"Name for sample"
    helpme["er_sample_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["er_expedition_name"]=	"Name for seagoing or land expedition"
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_section_name"]=	"Name for section or core"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_member_name"]=	"Name for member"
    helpme["er_site_name"]=	"Name for site"
    helpme["sample_class"]=	"General lithology type"
    helpme["sample_lithology"]=	"Sample lithology or archeological classification"
    helpme["sample_type"]=	"Sample type"
    helpme["sample_texture"]=	"Sample texture"
    helpme["sample_alteration"]=	"Sample alteration grade"
    helpme["sample_alteration_type"]=	"Sample alteration type"
    helpme["sample_lat"]=	"Sample location -- latitude"
    helpme["sample_lon"]=	"Sample location -- longitude"
    helpme["sample_location_precision"]=	"Sample location -- precision in latitude and longitude"
    helpme["sample_elevation"]=	"Sample location -- elevation relative to sealevel"
    helpme["sample_height"]=	"Sample location -- stratigraphic height"
    helpme["sample_drill_depth"]=	"Sample location -- depth in MBSF as used by ODP"
    helpme["sample_composite_depth"]=	"Sample location -- composite depth in MBSF as used by ODP"
    helpme["sample_date"]=	"Sampling date"
    helpme["sample_time_zone"]=	"Sampling time zone"
    helpme["sample_azimuth"]=	"Sample azimuth as measured clockwise from the north"
    helpme["sample_dip"]=	"Sample dip as measured into the outcrop"
    helpme["sample_bed_dip_direction"]=	"Direction of the dip of a paleo-horizontal plane in the bedding"
    helpme["sample_bed_dip"]=	"Dip of the bedding as measured to the right of strike direction"
    helpme["sample_cooling_rate"]=	"Estimated ancient in-situ cooling rate per Ma"
    helpme["er_specimen_name"]=	"Name for specimen"
    helpme["er_specimen_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["er_expedition_name"]=	"Name for seagoing or land expedition"
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_section_name"]=	"Name for section or core"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_member_name"]=	"Name for member"
    helpme["er_site_name"]=	"Name for site"
    helpme["er_sample_name"]=	"Name for sample"
    helpme["specimen_class"]=	"General lithology type"
    helpme["specimen_lithology"]=	"Specimen lithology or archeological classification"
    helpme["specimen_type"]=	"Specimen type"
    helpme["specimen_texture"]=	"Specimen texture"
    helpme["specimen_alteration"]=	"Specimen alteration grade"
    helpme["specimen_alteration_type"]=	"Specimen alteration type"
    helpme["specimen_elevation"]=	"Specimen location -- elevation relative to sealevel"
    helpme["specimen_height"]=	"Specimen location -- stratigraphic height"
    helpme["specimen_drill_depth"]=	"Specimen location -- depth in MBSF as used by ODP"
    helpme["specimen_composite_depth"]=	"Specimen location -- composite depth in MBSF as used by ODP"
    helpme["specimen_azimuth"]=	"Specimen azimuth as measured clockwise from the north"
    helpme["specimen_dip"]=	"Specimen dip as measured into the outcrop"
    helpme["specimen_volume"]=	"Specimen volume"
    helpme["specimen_weight"]=	"Specimen weight"
    helpme["specimen_density"]=	"Specimen density"
    helpme["specimen_size"]=	"Specimen grain size fraction"
    helpme["er_expedition_name"]=	"Name for seagoing or land expedition"
    helpme["er_location_name"]=	"Name for location or drill site"
    helpme["er_formation_name"]=	"Name for formation"
    helpme["er_member_name"]=	"Name for member"
    helpme["er_site_name"]=	"Name for site"
    helpme["er_sample_name"]=	"Name for sample"
    helpme["er_specimen_name"]=	"Name for specimen"
    helpme["er_fossil_name"]=	"Name for fossil"
    helpme["er_mineral_name"]=	"Name for mineral"
    helpme["GM-ALPHA"]=	"Age determination by using alpha counting"
    helpme["GM-ARAR"]=	"40Ar/39Ar age determination"
    helpme["GM-ARAR-AP"]=	"40Ar/39Ar age determination: Age plateau"
    helpme["GM-ARAR-II"]=	"40Ar/39Ar age determination: Inverse isochron"
    helpme["GM-ARAR-NI"]=	"40Ar/39Ar age determination: Normal isochron"
    helpme["GM-ARAR-TF"]=	"40Ar/39Ar age determination: Total fusion or recombined age"
    helpme["GM-C14"]=	"Radiocarbon age determination"
    helpme["GM-C14-AMS"]=	"Radiocarbon age determination: AMS"
    helpme["GM-C14-BETA"]=	"Radiocarbon age determination: Beta decay counting"
    helpme["GM-C14-CAL"]=	"Radiocarbon age determination: Calibrated"
    helpme["GM-CC"]=	"Correlation chronology"
    helpme["GM-CC-ARCH"]=	"Correlation chronology: Archeology"
    helpme["GM-CC-ARM"]=	"Correlation chronology: ARM"
    helpme["GM-CC-ASTRO"]=	"Correlation chronology: Astronomical"
    helpme["GM-CC-CACO3"]=	"Correlation chronology: Calcium carbonate"
    helpme["GM-CC-COLOR"]=	"Correlation chronology: Color or reflectance"
    helpme["GM-CC-GRAPE"]=	"Correlation chronology: Gamma Ray Polarimeter Experiment"
    helpme["GM-CC-IRM"]=	"Correlation chronology: IRM"
    helpme["GM-CC-ISO"]=	"Correlation chronology: Stable isotopes"
    helpme["GM-CC-REL"]=	"Correlation chronology: Relative chronology other than stratigraphic successions"
    helpme["GM-CC-STRAT"]=	"Correlation chronology: Stratigraphic succession"
    helpme["GM-CC-TECT"]=	"Correlation chronology: Tectites and microtectites"
    helpme["GM-CC-TEPH"]=	"Correlation chronology: Tephrochronology"
    helpme["GM-CC-X"]=	"Correlation chronology: Susceptibility"
    helpme["GM-CHEM"]=	"Chemical chronology"
    helpme["GM-CHEM-AAR"]=	"Chemical chronology: Amino acid racemization"
    helpme["GM-CHEM-OH"]=	"Chemical chronology: Obsidian hydration"
    helpme["GM-CHEM-SC"]=	"Chemical chronology: Stoan coatings CaCO3"
    helpme["GM-CHEM-TH"]=	"Chemical chronology: Tephra hydration"
    helpme["GM-COSMO"]=	"Cosmogenic age determination"
    helpme["GM-COSMO-AL26"]=	"Cosmogenic age determination: 26Al"
    helpme["GM-COSMO-AR39"]=	"Cosmogenic age determination: 39Ar"
    helpme["GM-COSMO-BE10"]=	"Cosmogenic age determination: 10Be"
    helpme["GM-COSMO-C14"]=	"Cosmogenic age determination: 14C"
    helpme["GM-COSMO-CL36"]=	"Cosmogenic age determination: 36Cl"
    helpme["GM-COSMO-HE3"]=	"Cosmogenic age determination: 3He"
    helpme["GM-COSMO-KR81"]=	"Cosmogenic age determination: 81Kr"
    helpme["GM-COSMO-NE21"]=	"Cosmogenic age determination: 21Ne"
    helpme["GM-COSMO-NI59"]=	"Cosmogenic age determination: 59Ni"
    helpme["GM-COSMO-SI32"]=	"Cosmogenic age determination: 32Si"
    helpme["GM-DENDRO"]=	"Dendrochronology"
    helpme["GM-ESR"]=	"Electron Spin Resonance"
    helpme["GM-FOSSIL"]=	"Age determined from fossil record"
    helpme["GM-FT"]=	"Fission track age determination"
    helpme["GM-HIST"]=	"Historically recorded geological event"
    helpme["GM-INT"]=	"Age determination through interpolation between at least two geological units of known age"
    helpme["GM-INT-L"]=	"Age determination through interpolation between at least two geological units of known age: Linear"
    helpme["GM-INT-S"]=	"Age determination through interpolation between at least two geological units of known age: Cubic spline"
    helpme["GM-ISO"]=	"Age determined by isotopic dating, but no further details available"
    helpme["GM-KAR"]=	"40K-40Ar age determination"
    helpme["GM-KAR-I"]=	"40K-40Ar age determination: Isochron"
    helpme["GM-KAR-MA"]=	"40K-40Ar age determination: Model age"
    helpme["GM-KCA"]=	"40K-40Ca age determination"
    helpme["GM-KCA-I"]=	"40K-40Ca age determination: Isochron"
    helpme["GM-KCA-MA"]=	"40K-40Ca age determination: Model age"
    helpme["GM-LABA"]=	"138La-138Ba age determination"
    helpme["GM-LABA-I"]=	"138La-138Ba age determination: Isochron"
    helpme["GM-LABA-MA"]=	"138La-138Ba age determination: Model age"
    helpme["GM-LACE"]=	"138La-138Ce age determination"
    helpme["GM-LACE-I"]=	"138La-138Ce age determination: Isochron"
    helpme["GM-LACE-MA"]=	"138La-138Ce age determination: Model age"
    helpme["GM-LICHE"]=	"Lichenometry"
    helpme["GM-LUHF"]=	"176Lu-176Hf age determination"
    helpme["GM-LUHF-I"]=	"176Lu-176Hf age determination: Isochron"
    helpme["GM-LUHF-MA"]=	"176Lu-176Hf age determination: Model age"
    helpme["GM-LUM"]=	"Luminescence"
    helpme["GM-LUM-IRS"]=	"Luminescence: Infrared stimulated luminescence"
    helpme["GM-LUM-OS"]=	"Luminescence: Optically stimulated luminescence"
    helpme["GM-LUM-TH"]=	"Luminescence: Thermoluminescence"
    helpme["GM-MOD"]=	"Model curve fit to available age dates"
    helpme["GM-MOD-L"]=	"Model curve fit to available age dates: Linear"
    helpme["GM-MOD-S"]=	"Model curve fit to available age dates: Cubic spline"
    helpme["GM-MORPH"]=	"Geomorphic chronology"
    helpme["GM-MORPH-DEF"]=	"Geomorphic chronology: Rate of deformation"
    helpme["GM-MORPH-DEP"]=	"Geomorphic chronology: Rate of deposition"
    helpme["GM-MORPH-POS"]=	"Geomorphic chronology: Geomorphology position"
    helpme["GM-MORPH-WEATH"]=	"Geomorphic chronology: Rock and mineral weathering"
    helpme["GM-NO"]=	"Unknown geochronology method"
    helpme["GM-O18"]=	"Oxygen isotope dating"
    helpme["GM-PBPB"]=	"207Pb-206Pb age determination"
    helpme["GM-PBPB-C"]=	"207Pb-206Pb age determination: Common Pb"
    helpme["GM-PBPB-I"]=	"207Pb-206Pb age determination: Isochron"
    helpme["GM-PLEO"]=	"Pleochroic haloes"
    helpme["GM-PMAG-ANOM"]=	"Paleomagnetic age determination: Magnetic anomaly identification"
    helpme["GM-PMAG-APWP"]=	"Paleomagnetic age determination: Comparing paleomagnetic data to APWP"
    helpme["GM-PMAG-ARCH"]=	"Paleomagnetic age determination: Archeomagnetism"
    helpme["GM-PMAG-DIR"]=	"Paleomagnetic age determination: Directions"
    helpme["GM-PMAG-POL"]=	"Paleomagnetic age determination: Polarities"
    helpme["GM-PMAG-REGSV"]=	"Paleomagnetic age determination: Correlation to a regional secular variation curve"
    helpme["GM-PMAG-RPI"]=	"Paleomagnetic age determination: Relative paleointensity"
    helpme["GM-PMAG-VEC"]=	"Paleomagnetic age determination: Full vector"
    helpme["GM-RATH"]=	"226Ra-230Th age determination"
    helpme["GM-RBSR"]=	"87Rb-87Sr age determination"
    helpme["GM-RBSR-I"]=	"87Rb-87Sr age determination: Isochron"
    helpme["GM-RBSR-MA"]=	"87Rb-87Sr age determination: Model age"
    helpme["GM-REOS"]=	"187Re-187Os age determination"
    helpme["GM-REOS-I"]=	"187Re-187Os age determination: Isochron"
    helpme["GM-REOS-MA"]=	"187Re-187Os age determination: Model age"
    helpme["GM-REOS-PT"]=	"187Re-187Os age determination: Pt normalization of 186Os"
    helpme["GM-SCLERO"]=	"Screlochronology"
    helpme["GM-SHRIMP"]=	"SHRIMP age dating"
    helpme["GM-SMND"]=	"147Sm-143Nd age determination"
    helpme["GM-SMND-I"]=	"147Sm-143Nd age determination: Isochron"
    helpme["GM-SMND-MA"]=	"147Sm-143Nd age determination: Model age"
    helpme["GM-THPB"]=	"232Th-208Pb age determination"
    helpme["GM-THPB-I"]=	"232Th-208Pb age determination: Isochron"
    helpme["GM-THPB-MA"]=	"232Th-208Pb age determination: Model age"
    helpme["GM-UPA"]=	"235U-231Pa age determination"
    helpme["GM-UPB"]=	"U-Pb age determination"
    helpme["GM-UPB-CC-T0"]=	"U-Pb age determination: Concordia diagram age, upper intersection"
    helpme["GM-UPB-CC-T1"]=	"U-Pb age determination: Concordia diagram age, lower intersection"
    helpme["GM-UPB-I-206"]=	"U-Pb age determination: 238U-206Pb isochron"
    helpme["GM-UPB-I-207"]=	"U-Pb age determination: 235U-207Pb isochron"
    helpme["GM-UPB-MA-206"]=	"U-Pb age determination: 238U-206Pb model age"
    helpme["GM-UPB-MA-207"]=	"U-Pb age determination: 235U-207Pb model age"
    helpme["GM-USD"]=	"Uranium series disequilibrium age determination"
    helpme["GM-USD-PA231-TH230"]=	"Uranium series disequilibrium age determination: 231Pa-230Th"
    helpme["GM-USD-PA231-U235"]=	"Uranium series disequilibrium age determination: 231Pa-235U"
    helpme["GM-USD-PB210"]=	"Uranium series disequilibrium age determination: 210Pb"
    helpme["GM-USD-RA226-TH230"]=	"Uranium series disequilibrium age determination: 226Ra-230Th"
    helpme["GM-USD-RA228-TH232"]=	"Uranium series disequilibrium age determination: 228Ra-232Th"
    helpme["GM-USD-TH228-TH232"]=	"Uranium series disequilibrium age determination: 228Th-232Th"
    helpme["GM-USD-TH230"]=	"Uranium series disequilibrium age determination: 230Th"
    helpme["GM-USD-TH230-TH232"]=	"Uranium series disequilibrium age determination: 230Th-232Th"
    helpme["GM-USD-TH230-U234"]=	"Uranium series disequilibrium age determination: 230Th-234U"
    helpme["GM-USD-TH230-U238"]=	"Uranium series disequilibrium age determination: 230Th-238U"
    helpme["GM-USD-U234-U238"]=	"Uranium series disequilibrium age determination: 234U-238U"
    helpme["GM-UTH"]=	"238U-230Th age determination"
    helpme["GM-UTHHE"]=	"U-Th-He age determination"
    helpme["GM-UTHPB"]=	"U-Th-Pb age determination"
    helpme["GM-UTHPB-CC-T0"]=	"U-Th-Pb age determination: Concordia diagram intersection age, upper intercept"
    helpme["GM-UTHPB-CC-T1"]=	"U-Th-Pb age determination: Concordia diagram intersection age, lower intercept"
    helpme["GM-VARVE"]=	"Age determined by varve counting"
    helpme["tiepoint_name"]=	"Name for tiepoint horizon"
    helpme["tiepoint_alternatives"]=	"Colon-delimited list of alternative names and abbreviations"
    helpme["tiepoint_height"]=	"Tiepoint stratigraphic height relative to reference tiepoint"
    helpme["tiepoint_height_sigma"]=	"Tiepoint stratigraphic height uncertainty"
    helpme["tiepoint_elevation"]=	"Tiepoint elevation relative to sealevel"
    helpme["tiepoint_type"]=	"Tiepoint type"
    helpme["age"]=	"Age"
    helpme["age_sigma"]=	"Age -- uncertainty"
    helpme["age_range_low"]=	"Age -- low range"
    helpme["age_range_high"]=	"Age -- high range"
    helpme["age_unit"]=	"Age -- unit"
    helpme["timescale_eon"]=	"Timescale eon"
    helpme["timescale_era"]=	"Timescale era"
    helpme["timescale_period"]=	"Timescale period"
    helpme["timescale_epoch"]=	"Timescale epoch"
    helpme["timescale_stage"]=	"Timescale stage"
    helpme["biostrat_zone"]=	"Biostratigraphic zone"
    helpme["conodont_zone"]=	"Conodont zone"
    helpme["magnetic_reversal_chron"]=	"Magnetic reversal chron"
    helpme["astronomical_stage"]=	"Astronomical stage name"
    helpme["oxygen_stage"]=	"Oxygen stage name"
    helpme["age_culture_name"]=	"Age culture name"
    return helpme[keyhelp]

def dosundec(sundata):
    """
    returns the declination for a given set of suncompass data
    INPUT:
      sundata={'date':'yyyy:mm:dd:hr:min','delta_u':DU,'lat':LAT,'lon':LON,'shadow_angle':SHADAZ}
      where:
         DU is the hours to subtract from local time to get Greenwich Mean Time
         LAT,LON are the site latitude,longitude (negative for south and west respectively)
         SHADAZ is the shadow angle of the desired direction with respect to the sun.
    OUTPUT:
      the declination of the desired direction wrt true north.
    """
    rad=numpy.pi/180.
    iday=0
    timedate=sundata["date"]
    timedate=timedate.split(":")
    year=int(timedate[0])
    mon=int(timedate[1])
    day=int(timedate[2])
    hours=float(timedate[3])
    min=float(timedate[4])
    du=int(sundata["delta_u"])
    hrs=hours-du
    if hrs > 24:
        day+=1
        hrs=hrs-24
    if hrs < 0:
        day=day-1
        hrs=hrs+24
    julian_day=julian(mon,day,year)
    utd=(hrs+min/60.)/24.
    greenwich_hour_angle,delta=gha(julian_day,utd)
    H=greenwich_hour_angle+float(sundata["lon"])
    if H > 360: H=H-360
    lat=float(sundata["lat"])
    if H > 90 and H < 270:lat=-lat
# now do spherical trig to get azimuth to sun
    lat=(lat)*rad
    delta=(delta)*rad
    H=H*rad
    ctheta=numpy.sin(lat)*numpy.sin(delta)+numpy.cos(lat)*numpy.cos(delta)*numpy.cos(H)
    theta=numpy.arccos(ctheta)
    beta=numpy.cos(delta)*numpy.sin(H)/numpy.sin(theta)
#
#       check which beta
#
    beta=numpy.arcsin(beta)/rad
    if delta < lat: beta=180-beta
    sunaz=180-beta
    suncor=(sunaz+float(sundata["shadow_angle"]))%360. #  mod 360
    return suncor

def gha(julian_day,f):
    """
    returns greenwich hour angle
    """
    rad=numpy.pi/180.
    d=julian_day-2451545.0+f
    L= 280.460 + 0.9856474*d
    g=  357.528 + 0.9856003*d
    L=L%360.
    g=g%360.
# ecliptic longitude
    lamb=L+1.915*numpy.sin(g*rad)+.02*numpy.sin(2*g*rad)
# obliquity of ecliptic
    epsilon= 23.439 - 0.0000004*d
# right ascension (in same quadrant as lambda)
    t=(numpy.tan((epsilon*rad)/2))**2
    r=1/rad
    rl=lamb*rad
    alpha=lamb-r*t*numpy.sin(2*rl)+(r/2)*t*t*numpy.sin(4*rl)
#       alpha=mod(alpha,360.0)
# declination
    delta=numpy.sin(epsilon*rad)*numpy.sin(lamb*rad)
    delta=numpy.arcsin(delta)/rad
# equation of time
    eqt=(L-alpha)
#
    utm=f*24*60
    H=utm/4+eqt+180
    H=H%360.0
    return H,delta

def julian(mon,day,year):
    """
    returns julian day
    """
    ig=15+31*(10+12*1582)
    if year == 0:
        print "Julian no can do"
        return
    if year < 0: year=year+1
    if mon > 2:
        julian_year=year
        julian_month=mon+1
    else:
        julian_year=year-1
        julian_month=mon+13
    j1=int(365.25*julian_year)
    j2=int(30.6001*julian_month)
    j3=day+1720995
    julian_day=j1+j2+j3
    if day+31*(mon+12*year) >= ig:
        jadj=int(0.01*julian_year)
        julian_day=julian_day+2-jadj+int(0.25*jadj)
    return julian_day

def fillkeys(Recs):
    """
    reconciles keys of dictionaries within Recs.
    """
    keylist,OutRecs=[],[]
    for rec in Recs:
        for key in rec.keys():
            if key not in keylist:keylist.append(key)
    for rec in  Recs:
        for key in keylist:
            if key not in rec.keys(): rec[key]=""
        OutRecs.append(rec)
    return OutRecs,keylist

def fisher_mean(data):
    """
    call to fisher_mean(data) calculates fisher statistics for data, which is a list of [dec,inc] pairs.
    """
    R,Xbar,X,fpars=0,[0,0,0],[],{}
    N=len(data)
    if N <2:
       return fpars
    X=dir2cart(data)
    for i in range(len(X)):
        for c in range(3):
           Xbar[c]+=X[i][c]
    for c in range(3):
        R+=Xbar[c]**2
    R=numpy.sqrt(R)
    for c in range(3):
        Xbar[c]=Xbar[c]/R
    dir=cart2dir(Xbar)
    fpars["dec"]=dir[0]
    fpars["inc"]=dir[1]
    fpars["n"]=N
    fpars["r"]=R
    if N!=R:
        k=(N-1.)/(N-R)
        fpars["k"]=k
        csd=81./numpy.sqrt(k)
    else:
        fpars['k']='inf'
        csd=0.
    b=20.**(1./(N-1.)) -1
    a=1-b*(N-R)/R
    if a<-1:a=-1
    a95=numpy.arccos(a)*180./numpy.pi
    fpars["alpha95"]=a95
    fpars["csd"]=csd
    if a<0: fpars["alpha95"] = 180.0
    return fpars

def gausspars(data):
    """
    calculates gaussian statistics for data
    """
    N,mean,d=len(data),0.,0.
    if N<1: return "",""
    if N==1: return data[0],0
    for j in range(N):
       mean+=data[j]/float(N)
    for j in range(N):
       d+=(data[j]-mean)**2
    stdev=numpy.sqrt(d*(1./(float(N-1))))
    return mean,stdev

def weighted_mean(data):
    """
    calculates weighted mean of data
    """
    W,N,mean,d=0,len(data),0,0
    if N<1: return "",""
    if N==1: return data[0][0],0
    for x in data:
       W+=x[1] # sum of the weights
    for x in data:
       mean+=(float(x[1])*float(x[0]))/float(W)
    for x in data:
       d+=(float(x[1])/float(W))*(float(x[0])-mean)**2
    stdev=numpy.sqrt(d*(1./(float(N-1))))
    return mean,stdev

def lnpbykey(data,key0,key1): # calculate a fisher mean of key1 data for a group of key0
    PmagRec={}
    if len(data)>1:
        for rec in data:
            rec['dec']=float(rec[key1+'_dec'])
            rec['inc']=float(rec[key1+'_inc'])
        fpars=dolnp(data,key1+'_direction_type')
        PmagRec[key0+"_dec"]=fpars["dec"]
        PmagRec[key0+"_inc"]=fpars["inc"]
        PmagRec[key0+"_n"]=(fpars["n_total"])
        PmagRec[key0+"_n_lines"]=fpars["n_lines"]
        PmagRec[key0+"_n_planes"]=fpars["n_planes"]
        PmagRec[key0+"_r"]=fpars["R"]
        PmagRec[key0+"_k"]=fpars["K"]
        PmagRec[key0+"_alpha95"]=fpars["alpha95"]
        if int(PmagRec[key0+"_n_planes"])>0:
            PmagRec["magic_method_codes"]="DE-FM-LP"
        elif int(PmagRec[key0+"_n_lines"])>2:
            PmagRec["magic_method_codes"]="DE-FM"
    elif len(data)==1:
        PmagRec[key0+"_dec"]=data[0][key1+'_dec']
        PmagRec[key0+"_inc"]=data[0][key1+'_inc']
        PmagRec[key0+"_n"]='1'
        if data[0][key1+'_direction_type']=='l':
            PmagRec[key0+"_n_lines"]='1'
            PmagRec[key0+"_n_planes"]='0'
        if data[0][key1+'_direction_type']=='p':
            PmagRec[key0+"_n_planes"]='1'
            PmagRec[key0+"_n_lines"]='0'
        PmagRec[key0+"_alpha95"]=""
        PmagRec[key0+"_r"]=""
        PmagRec[key0+"_k"]=""
        PmagRec[key0+"_direction_type"]="l"
    return PmagRec

def fisher_by_pol(data):
    """
    input:    as in dolnp (list of dictionaries with 'dec' and 'inc')
    description: do fisher mean after splitting data into two polarity domains.
    output: three dictionaries:
        'A'= polarity 'A'
        'B = polarity 'B'
        'ALL'= switching polarity of 'B' directions, and calculate fisher mean of all data
    code modified from eqarea_ell.py b rshaar 1/23/2014
    """
    FisherByPoles={}
    DIblock,nameblock,locblock=[],[],[]
    for rec in data:
        if 'dec' in rec.keys() and 'inc' in rec.keys():
            DIblock.append([float(rec["dec"]),float(rec["inc"])]) # collect data for fisher calculation
        else:
            continue
        if 'name' in rec.keys():
            nameblock.append(rec['name'])
        else:
            nameblock.append("")
        if 'loc' in rec.keys():
            locblock.append(rec['loc'])
        else:
            locblock.append("")

    ppars=doprinc(array(DIblock)) # get principal directions
    reference_DI=[ppars['dec'],ppars['inc']] # choose the northerly declination principe component ("normal")
    if reference_DI[0]>90 and reference_DI[0]<270: # make reference direction in northern hemisphere
        reference_DI[0]=(reference_DI[0]+180.)%360
        reference_DI[1]=reference_DI[1]*-1.
    nDIs,rDIs,all_DI,npars,rpars=[],[],[],[],[]
    nlist,rlist,alllist="","",""
    nloclist,rloclist,allloclist="","",""
    for k in range(len(DIblock)):
        if angle([DIblock[k][0],DIblock[k][1]],reference_DI) > 90.:
            rDIs.append(DIblock[k])
            rlist=rlist+":"+nameblock[k]
            if locblock[k] not in rloclist:rloclist=rloclist+":"+locblock[k]
            all_DI.append( [(DIblock[k][0]+180.)%360.,-1.*DIblock[k][1]])
            alllist=alllist+":"+nameblock[k]
            if locblock[k] not in allloclist:allloclist=allloclist+":"+locblock[k]
        else:
            nDIs.append(DIblock[k])
            nlist=nlist+":"+nameblock[k]
            if locblock[k] not in nloclist:nloclist=nloclist+":"+locblock[k]
            all_DI.append(DIblock[k])
            alllist=alllist+":"+nameblock[k]
            if locblock[k] not in allloclist:allloclist=allloclist+":"+locblock[k]

    for mode in ['A','B','All']:
        if mode=='A' and len(nDIs)>2:
            fpars=fisher_mean(nDIs)
            fpars['sites']=nlist.strip(':')
            fpars['locs']=nloclist.strip(':')
            FisherByPoles[mode]=fpars
        elif mode=='B' and len(rDIs)>2:
            fpars=fisher_mean(rDIs)
            fpars['sites']=rlist.strip(':')
            fpars['locs']=rloclist.strip(':')
            FisherByPoles[mode]=fpars
        elif mode=='All' and len(all_DI)>2:
            fpars=fisher_mean(all_DI)
            fpars['sites']=alllist.strip(':')
            fpars['locs']=allloclist.strip(':')
            FisherByPoles[mode]=fpars
    return FisherByPoles

def dolnp(data,direction_type_key):
    """
    returns fisher mean, a95 for data  using method of mcfadden and mcelhinny '88 for lines and planes
    """
    if "tilt_correction" in data[0].keys():
        tc=data[0]["tilt_correction"]
    else:
        tc='-1'
    n_lines,n_planes=0,0
    X,L,fdata,dirV=[],[],[],[0,0,0]
    E=[0,0,0]
    fpars={}
#
# sort data  into lines and planes and collect cartesian coordinates
    for rec in data:
        cart=dir2cart([rec["dec"],rec["inc"]])[0]
        if direction_type_key in rec.keys() and rec[direction_type_key]=='p': # this is a pole to a plane
            n_planes+=1
            L.append(cart) # this is the "EL, EM, EN" array of MM88
        else: # this is a line
            n_lines+=1
            fdata.append([rec["dec"],rec["inc"],1.]) # collect data for fisher calculation
            X.append(cart)
            E[0]+=cart[0]
            E[1]+=cart[1]
            E[2]+=cart[2]
# set up initial points on the great circles
    V,XV=[],[]
    if n_planes !=0:
        if n_lines==0:
            V=dir2cart([180.,-45.,1.]) # set the initial direction arbitrarily
        else:
           R=numpy.sqrt(E[0]**2+E[1]**2+E[2]**2)
           for c in E:
               V.append(c/R) # set initial direction as mean of lines
        U=E[:]   # make a copy of E
        for pole in L:
            XV.append(vclose(pole,V)) # get some points on the great circle
            for c in range(3):
               U[c]=U[c]+XV[-1][c]
# iterate to find best agreement
        angle_tol=1.
        while angle_tol > 0.1:
            angles=[]
            for k in range(n_planes):
               for c in range(3): U[c]=U[c]-XV[k][c]
               R=numpy.sqrt(U[0]**2+U[1]**2+U[2]**2)
               for c in range(3):V[c]=U[c]/R
               XX=vclose(L[k],V)
               ang=XX[0]*XV[k][0]+XX[1]*XV[k][1]+XX[2]*XV[k][2]
               angles.append(numpy.arccos(ang)*180./numpy.pi)
               for c in range(3):
                   XV[k][c]=XX[c]
                   U[c]=U[c]+XX[c]
               amax =-1
               for ang in angles:
                   if ang > amax:amax=ang
               angle_tol=amax
# calculating overall mean direction and R
        U=E[:]
        for dir in XV:
            for c in range(3):U[c]=U[c]+dir[c]
        R=numpy.sqrt(U[0]**2+U[1]**2+U[2]**2)
        for c in range(3):U[c]=U[c]/R
# get dec and inc of solution points on gt circles
        dirV=cart2dir(U)
# calculate modified Fisher stats fo fit
        n_total=n_lines+n_planes
        NP=n_lines+0.5*n_planes
        if NP<1.1:NP=1.1
        if n_total-R !=0:
            K=(NP-1.)/(n_total-R)
            fac=(20.**(1./(NP-1.))-1.)
            fac=fac*(NP-1.)/K
            a=1.-fac/R
            a95=a
            if abs(a) > 1.0: a95=1.
            if a<0:a95=-a95
            a95=numpy.arccos(a95)*180./numpy.pi
        else:
            a95=0.
            K='inf'
    else:
        dir=fisher_mean(fdata)
        n_total,R,K,a95=dir["n"],dir["r"],dir["k"],dir["alpha95"]
        dirV[0],dirV[1]=dir["dec"],dir["inc"]
    fpars["tilt_correction"]=tc
    fpars["n_total"]='%i '% (n_total)
    fpars["n_lines"]='%i '% (n_lines)
    fpars["n_planes"]='%i '% (n_planes)
    fpars["R"]='%5.4f '% (R)
    if K!='inf':
        fpars["K"]='%6.0f '% (K)
    else:
        fpars["K"]=K
    fpars["alpha95"]='%7.1f '% (a95)
    fpars["dec"]='%7.1f '% (dirV[0])
    fpars["inc"]='%7.1f '% (dirV[1])
    return fpars

def vclose(L,V):
    """
    gets the closest vector
    """
    lam,X=0,[]
    for k in range(3):
        lam=lam+V[k]*L[k]
    beta=numpy.sqrt(1.-lam**2)
    for k in range(3):
        X.append( ((V[k]-lam*L[k])/beta))
    return X

def scoreit(pars,PmagSpecRec,accept,text,verbose):
    """
    gets a grade for a given set of data, spits out stuff
    """
    s=PmagSpecRec["er_specimen_name"]
    PmagSpecRec["measurement_step_min"]='%8.3e' % (pars["measurement_step_min"])
    PmagSpecRec["measurement_step_max"]='%8.3e' % (pars["measurement_step_max"])
    PmagSpecRec["measurement_step_unit"]=pars["measurement_step_unit"]
    PmagSpecRec["specimen_int_n"]='%i'%(pars["specimen_int_n"])
    PmagSpecRec["specimen_lab_field_dc"]='%8.3e'%(pars["specimen_lab_field_dc"])
    PmagSpecRec["specimen_int"]='%8.3e '%(pars["specimen_int"])
    PmagSpecRec["specimen_b"]='%5.3f '%(pars["specimen_b"])
    PmagSpecRec["specimen_q"]='%5.1f '%(pars["specimen_q"])
    PmagSpecRec["specimen_f"]='%5.3f '%(pars["specimen_f"])
    PmagSpecRec["specimen_fvds"]='%5.3f'%(pars["specimen_fvds"])
    PmagSpecRec["specimen_b_beta"]='%5.3f'%(pars["specimen_b_beta"])
    PmagSpecRec["specimen_int_mad"]='%7.1f'%(pars["specimen_int_mad"])
    PmagSpecRec["specimen_dec"]='%7.1f'%(pars["specimen_dec"])
    PmagSpecRec["specimen_inc"]='%7.1f'%(pars["specimen_inc"])
    PmagSpecRec["specimen_int_dang"]='%7.1f '%(pars["specimen_int_dang"])
    PmagSpecRec["specimen_drats"]='%7.1f '%(pars["specimen_drats"])
    PmagSpecRec["specimen_int_ptrm_n"]='%i '%(pars["specimen_int_ptrm_n"])
    PmagSpecRec["specimen_rsc"]='%6.4f '%(pars["specimen_rsc"])
    PmagSpecRec["specimen_md"]='%i '%(int(pars["specimen_md"]))
    PmagSpecRec["specimen_b_sigma"]='%5.3f '%(pars["specimen_b_sigma"])
    if 'specimen_scat' in pars.keys():PmagSpecRec['specimen_scat']=pars['specimen_scat']
    if 'specimen_gmax' in pars.keys():PmagSpecRec['specimen_gmax']='%5.3f'%(pars['specimen_gmax'])
    if 'specimen_frac' in pars.keys():PmagSpecRec['specimen_frac']='%5.3f'%(pars['specimen_frac'])
    #PmagSpecRec["specimen_Z"]='%7.1f'%(pars["specimen_Z"])
  # check score
   #
    kill=grade(PmagSpecRec,accept,'specimen_int')
    Grade=""
    if len(kill)==0:
        Grade='A'
    else:
        Grade='F'
    pars["specimen_grade"]=Grade
    if verbose==0:
        return pars,kill
    diffcum=0
    if pars['measurement_step_unit']=='K':
        outstr= "specimen     Tmin  Tmax  N  lab_field  B_anc  b  q  f(coe)  Fvds  beta  MAD  Dang  Drats  Nptrm  Grade  R  MD%  sigma  Gamma_max \n"
        pars_out= (s,(pars["measurement_step_min"]-273),(pars["measurement_step_max"]-273),(pars["specimen_int_n"]),1e6*(pars["specimen_lab_field_dc"]),1e6*(pars["specimen_int"]),pars["specimen_b"],pars["specimen_q"],pars["specimen_f"],pars["specimen_fvds"],pars["specimen_b_beta"],pars["specimen_int_mad"],pars["specimen_int_dang"],pars["specimen_drats"],pars["specimen_int_ptrm_n"],pars["specimen_grade"],numpy.sqrt(pars["specimen_rsc"]),int(pars["specimen_md"]), pars["specimen_b_sigma"],pars['specimen_gamma'])
        outstring= '%s %4.0f %4.0f %i %4.1f %4.1f %5.3f %5.1f %5.3f %5.3f %5.3f  %7.1f %7.1f %7.1f %s %s %6.3f %i %5.3f %7.1f' % pars_out +'\n'
    elif pars['measurement_step_unit']=='J':
        outstr= "specimen     Wmin  Wmax  N  lab_field  B_anc  b  q  f(coe)  Fvds  beta  MAD  Dang  Drats  Nptrm  Grade  R  MD%  sigma  ThetaMax DeltaMax GammaMax\n"
        pars_out= (s,(pars["measurement_step_min"]),(pars["measurement_step_max"]),(pars["specimen_int_n"]),1e6*(pars["specimen_lab_field_dc"]),1e6*(pars["specimen_int"]),pars["specimen_b"],pars["specimen_q"],pars["specimen_f"],pars["specimen_fvds"],pars["specimen_b_beta"],pars["specimen_int_mad"],pars["specimen_int_dang"],pars["specimen_drats"],pars["specimen_int_ptrm_n"],pars["specimen_grade"],numpy.sqrt(pars["specimen_rsc"]),int(pars["specimen_md"]), pars["specimen_b_sigma"],pars["specimen_theta"],pars["specimen_delta"],pars["specimen_gamma"])
        outstring= '%s %4.0f %4.0f %i %4.1f %4.1f %5.3f %5.1f %5.3f %5.3f %5.3f  %7.1f %7.1f %7.1f %s %s %6.3f %i %5.3f %7.1f %7.1f %7.1f' % pars_out +'\n'
    if pars["specimen_grade"]!="A":
        print '\n killed by:'
        for k in kill:
            print k,':, criterion set to: ',accept[k],', specimen value: ',pars[k]
        print '\n'
    print outstr
    print outstring
    return pars,kill

def b_vdm(B,lat):
    """
    Converts field values in tesla to v(a)dm in Am^2
    """
    rad=numpy.pi/180.
    fact=((6.371e6)**3)*1e7 # changed radius of the earth from 3.367e6 3/12/2010
    colat=(90.-lat) * rad
    return fact*B/(numpy.sqrt(1+3*(numpy.cos(colat)**2)))

def vdm_b(vdm,lat):
    """
    Converts v(a)dm to  field values in tesla
    """
    rad=numpy.pi/180.
    fact=((6.371e6)**3)*1e7 # changed radius of the earth from 3.367e6 3/12/2010
    colat=(90.-lat) * rad
    return vdm*(numpy.sqrt(1+3*(numpy.cos(colat)**2)))/fact

def binglookup(w1i,w2i):
    """
    Bingham statistics lookup table.
    """
    K={'0.06': {'0.02': ['-25.58', '-8.996'], '0.06': ['-9.043', '-9.043'], '0.04': ['-13.14', '-9.019']}, '0.22': {'0.08': ['-6.944', '-2.644'], '0.02': ['-25.63', '-2.712'], '0.20': ['-2.649', '-2.354'], '0.06': [ '-9.027', '-2.673'], '0.04': ['-13.17', '-2.695'], '0.14': ['-4.071', '-2.521'], '0.16': ['-3.518', '-2.470'], '0.10': ['-5.658', '-2.609'], '0.12': ['-4.757', '-2.568'], '0.18': ['-3.053', '-2.414'], '0.22': ['-2.289', '-2.289']}, '0.46': {'0.02': ['-25.12', '-0.250'], '0.08': ['-6.215', '0.000'], '0.06': ['-8.371', '-0.090'], '0.04': ['-12.58', '-0.173']}, '0.44': {'0.08': ['-6.305', '-0.186'], '0.02': ['-25.19', '-0.418'], '0.06': ['-8.454', '-0.270'], '0.04': ['-12.66', '-0.347'], '0.10': ['-4.955', '-0.097'], '0.12': ['-3.992', '0.000']}, '0.42': {'0.08': ['-6.388', '-0.374'], '0.02': ['-25.5', '-0.589'], '0.06': [ '-8.532', '-0.452'], '0.04': ['-12.73', '-0.523'], '0.14': ['-3.349', '-0.104'], '0.16': ['-2.741', '0.000'], '0.10': ['-5.045', '-0.290'], '0.12': ['-4.089', '-0.200']}, '0.40': {'0.08': ['-6.466', '-0.564'], '0.02': ['-25.31', '-0.762'], '0.20': ['-1.874', '-0.000'], '0.06': ['-8.604', '-0.636'], '0.04': ['-12.80', '-0.702'], '0.14': ['-3.446', '-0.312'], '0.16': ['-2.845', '-0.215'], '0.10': ['-5.126', '-0.486'] , '0.12': ['-4.179', '-0.402'], '0.18': ['-2.330', '-0.111']}, '0.08': {'0.02': ['-25.6', '-6.977'], '0.08': ['-7.035', '-7.035'], '0.06': ['-9.065', '-7.020'], '0.04': ['-13.16', '-6.999']}, '0.28': {'0.08': ['-6.827', '-1.828'], '0.28': ['-1.106', '-1.106'], '0.02': ['-25.57', '-1.939'], '0.20': ['-2.441', '-1.458'], '0.26': ['-1.406', '-1.203'], '0.24': ['-1.724', '-1.294'], '0.06': ['-8.928', '-1.871'], '0.04': ['-13.09', '-1.908'], '0.14': ['-3.906', '-1.665'], '0.16': ['-3.338', '-1.601'], '0.10': ['-5.523', '-1.779'], '0.12': ['-4.606', '-1.725'], '0.18': ['-2.859', '-1.532'], '0.22': ['-2.066', '-1.378']}, '0.02': {'0.02': ['-25.55','-25.55']}, '0.26': {'0.08': ['-6.870', '-2.078'], '0.02': ['-25.59', '-2.175'], '0.20': ['-2.515', '-1.735'], '0.26': ['-1.497', '-1.497'], '0.24': ['-1.809', '-1.582'], '0.06': ['-8.96 6', '-2.117'], '0.04': ['-13.12', '-2.149'], '0.14': ['-3.965', '-1.929'], '0.16': ['-3.403', '-1.869'], '0.10': ['-5.573', '-2.034'], '0.12': ['-4.661', '-1.984'], '0.18': ['-2.928', '-1.805'], '0.22': ['-2.1 46', '-1.661']}, '0.20': {'0.08': ['-6.974', '-2.973'], '0.02': ['-25.64', '-3.025'], '0.20': ['-2.709', '-2.709'], '0.06': ['-9.05', '-2.997'], '0.04': ['-13.18', '-3.014'], '0.14': ['-4.118', '-2.863'], '0.1 6': ['-3.570', '-2.816'], '0.10': ['-5.694', '-2.942'], '0.12': ['-4.799', '-2.905'], '0.18': ['-3.109', '-2.765']}, '0.04': {'0.02': ['-25.56', '-13.09'], '0.04': ['-13.11', '-13.11']}, '0.14': {'0.08': ['-7.  033', '-4.294'], '0.02': ['-25.64', '-4.295'], '0.06': ['-9.087', '-4.301'], '0.04': ['-13.20', '-4.301'], '0.14': ['-4.231', '-4.231'], '0.10': ['-5.773', '-4.279'], '0.12': ['-4.896', '-4.258']}, '0.16': {'0 .08': ['-7.019', '-3.777'], '0.02': ['-25.65', '-3.796'], '0.06': ['-9.081', '-3.790'], '0.04': ['-13.20', '-3.796'], '0.14': ['-4.198', '-3.697'], '0.16': ['-3.659', '-3.659'], '0.10': ['-5.752', '-3.756'], ' 0.12': ['-4.868', '-3.729']}, '0.10': {'0.02': ['-25.62', '-5.760'], '0.08': ['-7.042', '-5.798'], '0.06': ['-9.080', '-5.791'], '0.10': ['-5.797', '-5.797'], '0.04': ['-13.18', '-5.777']}, '0.12': {'0.08': [' -7.041', '-4.941'], '0.02': ['-25.63', '-4.923'], '0.06': ['-9.087', '-4.941'], '0.04': ['-13.19', '-4.934'], '0.10': ['-5.789', '-4.933'], '0.12': ['-4.917', '-4.917']}, '0.18': {'0.08': ['-6.999', '-3.345'], '0.02': ['-25.65', '-3.381'], '0.06': ['-9.068', '-3.363'], '0.04': ['-13.19', '-3.375'], '0.14': ['-4.160', '-3.249'], '0.16': ['-3.616', '-3.207'], '0.10': ['-5.726', '-3.319'], '0.12': ['-4.836', '-3.287'] , '0.18': ['-3.160', '-3.160']}, '0.38': {'0.08': ['-6.539', '-0.757'], '0.02': ['-25.37', '-0.940'], '0.20': ['-1.986', '-0.231'], '0.24': ['-1.202', '0.000'], '0.06': ['-8.670', '-0.824'], '0.04': ['-12.86', '-0.885'], '0.14': ['-3.536', '-0.522'], '0.16': ['-2.941', '-0.432'], '0.10': ['-5.207', '-0.684'], '0.12': ['-4.263', '-0.606'], '0.18': ['-2.434', '-0.335'], '0.22': ['-1.579', '-0.120']}, '0.36': {'0.08': ['-6.606', '-9.555'], '0.28': ['-0.642', '0.000'], '0.02': ['-25.42', '-1.123'], '0.20': ['-2.089', '-0.464'], '0.26': ['-0.974', '-0.129'], '0.24': ['-1.322', '-0.249'], '0.06': ['-8.731', '-1.017'], '0.04': ['-12.91', '-1.073'], '0.14': ['-3.620', '-0.736'], '0.16': ['-3.032', '-0.651'], '0.10': ['-5.280', '-0.887'], '0.12': ['-4.342', '-0.814'], '0.18': ['-2.531', '-0.561'], '0.22': ['-1.690', '-0.360']}, '0.34 ': {'0.08': ['-6.668', '-1.159'], '0.28': ['-0.771', '-0.269'], '0.02': ['-25.46', '-1.312'], '0.20': ['-2.186', '-0.701'], '0.26': ['-1.094', '-0.389'], '0.24': ['-1.433', '-0.500'], '0.06': ['-8.788', '-1.21 6'], '0.32': ['-0.152', '0.000'], '0.04': ['-12.96', '-1.267'], '0.30': ['-0.459', '-0.140'], '0.14': ['-3.699', '-0.955'], '0.16': ['-3.116', '-0.876'], '0.10': ['-5.348', '-1.096'], '0.12': ['-4.415', '-1.02 8'], '0.18': ['-2.621', '-0.791'], '0.22': ['-1.794', '-0.604']}, '0.32': {'0.08': ['-6.725', '-1.371'], '0.28': ['-0.891', '-0.541'], '0.02': ['-25.50', '-1.510'], '0.20': ['-2.277', '-0.944'], '0.26': ['-1.2 06', '-0.653'], '0.24': ['-1.537', '-0.756'], '0.06': ['-8.839', '-1.423'], '0.32': ['-0.292', '-0.292'], '0.04': ['-13.01', '-1.470'], '0.30': ['-0.588', '-0.421'], '0.14': ['-3.773', '-1.181'], '0.16': ['-3.  195', '-1.108'], '0.10': ['-5.411', '-1.313'], '0.12': ['-4.484', '-1.250'], '0.18': ['-2.706', '-1.028'], '0.22': ['-1.891', '-0.853']}, '0.30': {'0.08': ['-6.778', '-1.596'], '0.28': ['-1.002', '-0.819'], '0 .02': ['-25.54', '-1.718'], '0.20': ['-2.361', '-1.195'], '0.26': ['-1.309', '-0.923'], '0.24': ['-1.634', '-1.020'], '0.06': ['-8.886', '-1.641'], '0.04': ['-13.05', '-1.682'], '0.30': ['-0.708', '-0.708'], ' 0.14': ['-3.842', '-1.417'], '0.16': ['-3.269', '-1.348'], '0.10': ['-5.469', '-1.540'], '0.12': ['-4.547', '-1.481'], '0.18': ['-2.785', '-1.274'], '0.22': ['-1.981', '-1.110']}, '0.24': {'0.08': ['-6.910', ' -2.349'], '0.02': ['-25.61', '-2.431'], '0.20': ['-2.584', '-2.032'], '0.24': ['-1.888', '-1.888'], '0.06': ['-8.999', '-2.382'], '0.04': ['-23.14', '-2.410'], '0.14': ['-4.021', '-2.212'], '0.16': ['-3.463', '-2.157'], '0.10': ['-5.618', '-2.309'], '0.12': ['-4.711', '-2.263'], '0.18': ['-2.993', '-2.097'], '0.22': ['-2.220', '-1.963']}}
    w1,w2=0.,0.
    wstart,incr=0.01,0.02
    if w1i < wstart: w1='%4.2f'%(wstart+incr/2.)
    if w2i < wstart: w2='%4.2f'%(wstart+incr/2.)
    wnext=wstart+incr
    while wstart <0.5:
        if w1i >=wstart and w1i <wnext :
            w1='%4.2f'%(wstart+incr/2.)
        if w2i >=wstart and w2i <wnext :
            w2='%4.2f'%(wstart+incr/2.)
        wstart+=incr
        wnext+=incr
    k1,k2=float(K[w2][w1][0]),float(K[w2][w1][1])
    return  k1,k2

def cdfout(data,file):
    """
    spits out the cdf for data to file
    """
    f=open(file,"w")
    data.sort()
    for j in range(len(data)):
        y=float(j)/float(len(data))
        out=str(data[j])+' '+str(y)+ '\n'
        f.write(out)

def dobingham(data):
    """
    gets bingham parameters for data
    """
    control,X,bpars=[],[],{}
    N=len(data)
    if N <2:
       return bpars
#
#  get cartesian coordinates
#
    for rec in data:
        X.append(dir2cart([rec[0],rec[1],1.]))
#
#   put in T matrix
#
    T=numpy.array(Tmatrix(X))
    t,V=tauV(T)
    w1,w2,w3=t[2],t[1],t[0]
    k1,k2=binglookup(w1,w2)
    PDir=cart2dir(V[0])
    EDir=cart2dir(V[1])
    ZDir=cart2dir(V[2])
    if PDir[1] < 0:
        PDir[0]+=180.
        PDir[1]=-PDir[1]
    PDir[0]=PDir[0]%360.
    bpars["dec"]=PDir[0]
    bpars["inc"]=PDir[1]
    bpars["Edec"]=EDir[0]
    bpars["Einc"]=EDir[1]
    bpars["Zdec"]=ZDir[0]
    bpars["Zinc"]=ZDir[1]
    bpars["n"]=N
#
#  now for Bingham ellipses.
#
    fac1,fac2=-2*N*(k1)*(w3-w1),-2*N*(k2)*(w3-w2)
    sig31,sig32=numpy.sqrt(1./fac1), numpy.sqrt(1./fac2)
    bpars["Zeta"],bpars["Eta"]=2.45*sig31*180./numpy.pi,2.45*sig32*180./numpy.pi
    return  bpars

def doflip(dec,inc):
   """
   flips lower hemisphere data to upper hemisphere
   """
   if inc <0:
       inc=-inc
       dec=(dec+180.)%360.
   return dec,inc

def doincfish(inc):
    """
    gets fisher mean inc from inc only data
    """
    rad,SCOi,SSOi=numpy.pi/180.,0.,0. # some definitions
    abinc=[]
    for i in inc:abinc.append(abs(i))
    MI,std=gausspars(abinc) # get mean inc and standard deviation
    fpars={}
    N=len(inc)  # number of data
    fpars['n']=N
    fpars['ginc']=MI
    if MI<30:
        fpars['inc']=MI
        fpars['k']=0
        fpars['alpha95']=0
        fpars['csd']=0
        fpars['r']=0
        print 'WARNING: mean inc < 30, returning gaussian mean'
        return fpars
    for i in inc:  # sum over all incs (but take only positive inc)
        coinc=(90.-abs(i))*rad
        SCOi+= numpy.cos(coinc)
        SSOi+= numpy.sin(coinc)
    Oo=(90.0-MI)*rad # first guess at mean
    SCFlag = -1  # sign change flag
    epsilon = float(N)*numpy.cos(Oo) # RHS of zero equations
    epsilon+= (numpy.sin(Oo)**2-numpy.cos(Oo)**2)*SCOi
    epsilon-= 2.*numpy.sin(Oo)*numpy.cos(Oo)*SSOi
    while SCFlag < 0: # loop until cross zero
        if MI > 0 : Oo-=(.01*rad)  # get steeper
        if MI < 0 : Oo+=(.01*rad)  # get shallower
        prev=epsilon
        epsilon = float(N)*numpy.cos(Oo) # RHS of zero equations
        epsilon+= (numpy.sin(Oo)**2.-numpy.cos(Oo)**2.)*SCOi
        epsilon-= 2.*numpy.sin(Oo)*numpy.cos(Oo)*SSOi
        if abs(epsilon) > abs(prev): MI=-1*MI  # reverse direction
        if epsilon*prev < 0: SCFlag = 1 # changed sign
    S,C=0.,0.  # initialize for summation
    for i in inc:
        coinc=(90.-abs(i))*rad
        S+= numpy.sin(Oo-coinc)
        C+= numpy.cos(Oo-coinc)
    k=(N-1.)/(2.*(N-C))
    Imle=90.-(Oo/rad)
    fpars["inc"]=Imle
    fpars["r"],R=2.*C-N,2*C-N
    fpars["k"]=k
    f=fcalc(2,N-1)
    a95= 1. - (0.5)*(S/C)**2 - (f/(2.*C*k))
#    b=20.**(1./(N-1.)) -1.
#    a=1.-b*(N-R)/R
#    a95=numpy.arccos(a)*180./numpy.pi
    csd=81./numpy.sqrt(k)
    fpars["alpha95"]=a95
    fpars["csd"]=csd
    return fpars

def dokent(data,NN):
    """
    gets Kent  parameters for data ([D,I],N)
    """
    X,kpars=[],{}
    N=len(data)
    if N <2:
       return kpars
#
#  get fisher mean and convert to co-inclination (theta)/dec (phi) in radians
#
    fpars=fisher_mean(data)
    pbar=fpars["dec"]*numpy.pi/180.
    tbar=(90.-fpars["inc"])*numpy.pi/180.
#
#   initialize matrices
#
    H=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
    w=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
    b=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
    gam=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
    xg=[]
#
#  set up rotation matrix H
#
    H=[ [numpy.cos(tbar)*numpy.cos(pbar),-numpy.sin(pbar),numpy.sin(tbar)*numpy.cos(pbar)],[numpy.cos(tbar)*numpy.sin(pbar),numpy.cos(pbar),numpy.sin(pbar)*numpy.sin(tbar)],[-numpy.sin(tbar),0.,numpy.cos(tbar)]]
#
#  get cartesian coordinates of data
#
    for rec in data:
        X.append(dir2cart([rec[0],rec[1],1.]))
#
#   put in T matrix
#
    T=Tmatrix(X)
    for i in range(3):
        for j in range(3):
            T[i][j]=T[i][j]/float(NN)
#
# compute B=H'TH
#
    for i in range(3):
        for j in range(3):
            for k in range(3):
                w[i][j]+=T[i][k]*H[k][j]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                b[i][j]+=H[k][i]*w[k][j]
#
# choose a rotation w about North pole to diagonalize upper part of B
#
    psi = 0.5*numpy.arctan(2.*b[0][1]/(b[0][0]-b[1][1]))
    w=[[numpy.cos(psi),-numpy.sin(psi),0],[numpy.sin(psi),numpy.cos(psi),0],[0.,0.,1.]]
    for i in range(3):
        for j in range(3):
            gamtmp=0.
            for k in range(3):
                gamtmp+=H[i][k]*w[k][j]
            gam[i][j]=gamtmp
    for i in range(N):
        xg.append([0.,0.,0.])
        for k in range(3):
            xgtmp=0.
            for j in range(3):
                xgtmp+=gam[j][k]*X[i][j]
            xg[i][k]=xgtmp
# compute asymptotic ellipse parameters
#
    xmu,sigma1,sigma2=0.,0.,0.
    for  i in range(N):
        xmu+= xg[i][2]
        sigma1=sigma1+xg[i][1]**2
        sigma2=sigma2+xg[i][0]**2
    xmu=xmu/float(N)
    sigma1=sigma1/float(N)
    sigma2=sigma2/float(N)
    g=-2.0*numpy.log(0.05)/(float(NN)*xmu**2)
    if numpy.sqrt(sigma1*g)<1:eta=numpy.arcsin(numpy.sqrt(sigma1*g))
    if numpy.sqrt(sigma2*g)<1:zeta=numpy.arcsin(numpy.sqrt(sigma2*g))
    if numpy.sqrt(sigma1*g)>=1.:eta=numpy.pi/2.
    if numpy.sqrt(sigma2*g)>=1.:zeta=numpy.pi/2.
#
#  convert Kent parameters to directions,angles
#
    kpars["dec"]=fpars["dec"]
    kpars["inc"]=fpars["inc"]
    kpars["n"]=NN
    ZDir=cart2dir([gam[0][1],gam[1][1],gam[2][1]])
    EDir=cart2dir([gam[0][0],gam[1][0],gam[2][0]])
    kpars["Zdec"]=ZDir[0]
    kpars["Zinc"]=ZDir[1]
    kpars["Edec"]=EDir[0]
    kpars["Einc"]=EDir[1]
    if kpars["Zinc"]<0:
        kpars["Zinc"]=-kpars["Zinc"]
        kpars["Zdec"]=(kpars["Zdec"]+180.)%360.
    if kpars["Einc"]<0:
        kpars["Einc"]=-kpars["Einc"]
        kpars["Edec"]=(kpars["Edec"]+180.)%360.
    kpars["Zeta"]=zeta*180./numpy.pi
    kpars["Eta"]=eta*180./numpy.pi
    return kpars

def doprinc(data):
    """
    gets principal components from data in form of an array of [dec,inc] data.
    """
    ppars={}
    rad=numpy.pi/180.
    X=dir2cart(data)
    #for rec in data:
    #    dir=[]
    #    for c in rec: dir.append(c)
    #    cart= (dir2cart(dir))
    #    X.append(cart)
#   put in T matrix
#
    T=numpy.array(Tmatrix(X))
#
#   get sorted evals/evects
#
    t,V=tauV(T)
    Pdir=cart2dir(V[0])
    ppars['Edir']=cart2dir(V[1]) # elongation direction
    dec,inc=doflip(Pdir[0],Pdir[1])
    ppars['dec']=dec
    ppars['inc']=inc
    ppars['N']=len(data)
    ppars['tau1']=t[0]
    ppars['tau2']=t[1]
    ppars['tau3']=t[2]
    Pdir=cart2dir(V[1])
    dec,inc=doflip(Pdir[0],Pdir[1])
    ppars['V2dec']=dec
    ppars['V2inc']=inc
    Pdir=cart2dir(V[2])
    dec,inc=doflip(Pdir[0],Pdir[1])
    ppars['V3dec']=dec
    ppars['V3inc']=inc
    return ppars

def PTrot(EP,Lats,Lons):
    """ Does rotation of points on a globe  by finite rotations, using method of Cox and Hart 1986, box 7-3. """
# gets user input of Rotation pole lat,long, omega for plate and converts to radians
    E=dir2cart([EP[1],EP[0],1.])
    omega=EP[2]*numpy.pi/180.
    RLats,RLons=[],[]
    for k in range(len(Lats)):
      if Lats[k]<=90.: # peel off delimiters
# converts to rotation pole to cartesian coordinates
        A=dir2cart([Lons[k],Lats[k],1.])
# defines cartesian coordinates of the pole A
        R=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]]
        R[0][0]=E[0]*E[0]*(1-numpy.cos(omega)) + numpy.cos(omega)
        R[0][1]=E[0]*E[1]*(1-numpy.cos(omega)) - E[2]*numpy.sin(omega)
        R[0][2]=E[0]*E[2]*(1-numpy.cos(omega)) + E[1]*numpy.sin(omega)
        R[1][0]=E[1]*E[0]*(1-numpy.cos(omega)) + E[2]*numpy.sin(omega)
        R[1][1]=E[1]*E[1]*(1-numpy.cos(omega)) + numpy.cos(omega)
        R[1][2]=E[1]*E[2]*(1-numpy.cos(omega)) - E[0]*numpy.sin(omega)
        R[2][0]=E[2]*E[0]*(1-numpy.cos(omega)) - E[1]*numpy.sin(omega)
        R[2][1]=E[2]*E[1]*(1-numpy.cos(omega)) + E[0]*numpy.sin(omega)
        R[2][2]=E[2]*E[2]*(1-numpy.cos(omega)) + numpy.cos(omega)
# sets up rotation matrix
        Ap=[0,0,0]
        for i in range(3):
            for j in range(3):
                Ap[i]+=R[i][j]*A[j]
# does the rotation
        Prot=cart2dir(Ap)
        RLats.append(Prot[1])
        RLons.append(Prot[0])
      else:  # preserve delimiters
        RLats.append(Lats[k])
        RLons.append(Lons[k])
    return RLats,RLons

def dread(infile,cols):
    """
     reads in specimen, tr, dec, inc int into data[].  position of
     tr, dec, inc, int determined by cols[]
    """
    data=[]
    f=open(infile,"rU")
    for line in f.readlines():
        tmp=line.split()
        rec=(tmp[0],float(tmp[cols[0]]),float(tmp[cols[1]]),float(tmp[cols[2]]),
          float(tmp[cols[3]]) )
        data.append(rec)
    return data

def fshdev(k):
    """
    a call to fshdev(k), where k is kappa, returns a direction from distribution with mean declination of 0, inclination of 90 and kappa of k
    """
    R1=random.random()
    R2=random.random()
    L=numpy.exp(-2*k)
    a=R1*(1-L)+L
    fac=numpy.sqrt((-numpy.log(a))/(2*k))
    inc=90.-2*numpy.arcsin(fac)*180./numpy.pi
    dec=2*numpy.pi*R2*180./numpy.pi
    return dec,inc

def lowes(data):
    """
    gets Lowe's power spectrum from infile - writes to ofile
    """
    Ls=range(1,9)
    Rs=[]
    recno=0
    for l in Ls:
        pow=0
        for m in range(0,l+1):
            pow+=(l+1)*((1e-3*data[recno][2])**2+(1e-3*data[recno][3])**2)
            recno+=1
        Rs.append(pow)
    return Ls,Rs

def magnetic_lat(inc):
    """
    returns magnetic latitude from inclination
    """
    rad=numpy.pi/180.
    paleo_lat=numpy.arctan( 0.5*numpy.tan(inc*rad))/rad
    return paleo_lat

def check_F(AniSpec):
    s=numpy.zeros((6),'f')
    s[0]=float(AniSpec["anisotropy_s1"])
    s[1]=float(AniSpec["anisotropy_s2"])
    s[2]=float(AniSpec["anisotropy_s3"])
    s[3]=float(AniSpec["anisotropy_s4"])
    s[4]=float(AniSpec["anisotropy_s5"])
    s[5]=float(AniSpec["anisotropy_s6"])
    chibar=(s[0]+s[1]+s[2])/3.
    tau,Vdir=doseigs(s)
    t2sum=0
    for i in range(3): t2sum+=tau[i]**2
    if 'anisotropy_sigma' in AniSpec.keys() and 'anisotropy_n' in AniSpec.keys():
        if AniSpec['anisotropy_type']=='AMS':
            nf=int(AniSpec["anisotropy_n"])-6
        else:
            nf=3*int(AniSpec["anisotropy_n"])-6
        sigma=float(AniSpec["anisotropy_sigma"])
        F=0.4*(t2sum-3*chibar**2)/(sigma**2)
        Fcrit=fcalc(5,nf)
        if F>Fcrit: # anisotropic
            chi=numpy.array([[s[0],s[3],s[5]],[s[3],s[1],s[4]],[s[5],s[4],s[2]]])
            chi_inv=numpy.linalg.inv(chi)
            #trace=chi_inv[0][0]+chi_inv[1][1]+chi_inv[2][2] # don't normalize twice
            #chi_inv=3.*chi_inv/trace
        else: # isotropic
            chi_inv=numpy.array([[1.,0,0],[0,1.,0],[0,0,1.]]) # make anisotropy tensor identity tensor
            chi=chi_inv
    else: # no sigma key available - just do the correction
        print 'WARNING: NO FTEST ON ANISOTROPY PERFORMED BECAUSE OF MISSING SIGMA - DOING CORRECTION ANYWAY'
        chi=numpy.array([[s[0],s[3],s[5]],[s[3],s[1],s[4]],[s[5],s[4],s[2]]])
        chi_inv=numpy.linalg.inv(chi)
    return chi,chi_inv

def Dir_anis_corr(InDir,AniSpec):
    """
    takes the 6 element 's' vector and the Dec,Inc 'InDir' data,
    performs simple anisotropy correction. returns corrected Dec, Inc
    """
    Dir=numpy.zeros((3),'f')
    Dir[0]=InDir[0]
    Dir[1]=InDir[1]
    Dir[2]=1.
    chi,chi_inv=check_F(AniSpec)
    if chi[0][0]==1.:return Dir # isotropic
    X=dir2cart(Dir)
    M=numpy.array(X)
    H=numpy.dot(M,chi_inv)
    return cart2dir(H)

def doaniscorr(PmagSpecRec,AniSpec):
    """
    takes the 6 element 's' vector and the Dec,Inc, Int 'Dir' data,
    performs simple anisotropy correction. returns corrected Dec, Inc, Int
    """
    AniSpecRec={}
    for key in PmagSpecRec.keys():
        AniSpecRec[key]=PmagSpecRec[key]
    Dir=numpy.zeros((3),'f')
    Dir[0]=float(PmagSpecRec["specimen_dec"])
    Dir[1]=float(PmagSpecRec["specimen_inc"])
    Dir[2]=float(PmagSpecRec["specimen_int"])
# check if F test passes!  if anisotropy_sigma available
    chi,chi_inv=check_F(AniSpec)
    if chi[0][0]==1.: # isotropic
        cDir=[Dir[0],Dir[1]] # no change
        newint=Dir[2]
    else:
        X=dir2cart(Dir)
        M=numpy.array(X)
        H=numpy.dot(M,chi_inv)
        cDir= cart2dir(H)
        Hunit=[H[0]/cDir[2],H[1]/cDir[2],H[2]/cDir[2]] # unit vector parallel to Banc
        Zunit=[0,0,-1.] # unit vector parallel to lab field
        Hpar=numpy.dot(chi,Hunit) # unit vector applied along ancient field
        Zpar=numpy.dot(chi,Zunit) # unit vector applied along lab field
        HparInt=cart2dir(Hpar)[2] # intensity of resultant vector from ancient field
        ZparInt=cart2dir(Zpar)[2] # intensity of resultant vector from lab field
        newint=Dir[2]*ZparInt/HparInt
        if cDir[0]-Dir[0]>90:
            cDir[1]=-cDir[1]
            cDir[0]=(cDir[0]-180.)%360.
    AniSpecRec["specimen_dec"]='%7.1f'%(cDir[0])
    AniSpecRec["specimen_inc"]='%7.1f'%(cDir[1])
    AniSpecRec["specimen_int"]='%9.4e'%(newint)
    AniSpecRec["specimen_correction"]='c'
    if 'magic_method_codes' in AniSpecRec.keys():
        methcodes=AniSpecRec["magic_method_codes"]
    else:
        methcodes=""
    if methcodes=="": methcodes="DA-AC-"+AniSpec['anisotropy_type']
    if methcodes!="": methcodes=methcodes+":DA-AC-"+AniSpec['anisotropy_type']
    if chi[0][0]==1.: # isotropic
        methcodes= methcodes+':DA-AC-ISO' # indicates anisotropy was checked and no change necessary
    AniSpecRec["magic_method_codes"]=methcodes.strip(":")
    return AniSpecRec

def vfunc(pars_1,pars_2):
    """
    returns 2*(Sw-Rw) for Watson's V
    """
    cart_1=dir2cart([pars_1["dec"],pars_1["inc"],pars_1["r"]])
    cart_2=dir2cart([pars_2['dec'],pars_2['inc'],pars_2["r"]])
    Sw=pars_1['k']*pars_1['r']+pars_2['k']*pars_2['r'] # k1*r1+k2*r2
    xhat_1=pars_1['k']*cart_1[0]+pars_2['k']*cart_2[0] # k1*x1+k2*x2
    xhat_2=pars_1['k']*cart_1[1]+pars_2['k']*cart_2[1] # k1*y1+k2*y2
    xhat_3=pars_1['k']*cart_1[2]+pars_2['k']*cart_2[2] # k1*z1+k2*z2
    Rw=numpy.sqrt(xhat_1**2+xhat_2**2+xhat_3**2)
    return 2*(Sw-Rw)

def vgp_di(plat,plong,slat,slong):
    """
    returns direction for a given observation site from a Virtual geomagnetic pole
    """
    rad,signdec=numpy.pi/180.,1.
    delphi=abs(plong-slong)
    if delphi!=0:signdec=(plong-slong)/delphi
    if slat==90.:slat=89.99
    thetaS=(90.-slat)*rad
    thetaP=(90.-plat)*rad
    delphi=delphi*rad
    cosp=numpy.cos(thetaS)*numpy.cos(thetaP)+numpy.sin(thetaS)*numpy.sin(thetaP)*numpy.cos(delphi)
    thetaM=numpy.arccos(cosp)
    cosd=(numpy.cos(thetaP)-numpy.cos(thetaM)*numpy.cos(thetaS))/(numpy.sin(thetaM)*numpy.sin(thetaS))
    C=abs(1.-cosd**2)
    if C!=0:
         dec=-numpy.arctan(cosd/numpy.sqrt(abs(C)))+numpy.pi/2.
    else:
        dec=numpy.arccos(cosd)
    if -numpy.pi<signdec*delphi and signdec<0: dec=2.*numpy.pi-dec  # checking quadrant
    if signdec*delphi> numpy.pi: dec=2.*numpy.pi-dec
    dec=(dec/rad)%360.
    inc=(numpy.arctan2(2.*numpy.cos(thetaM),numpy.sin(thetaM)))/rad
    return  dec,inc

def watsonsV(Dir1,Dir2):
    """
    calculates Watson's V statistic for two sets of directions
    """
    counter,NumSims=0,500
#
# first calculate the fisher means and cartesian coordinates of each set of Directions
#
    pars_1=fisher_mean(Dir1)
    pars_2=fisher_mean(Dir2)
#
# get V statistic for these
#
    V=vfunc(pars_1,pars_2)
#
# do monte carlo simulation of datasets with same kappas, but common mean
#
    Vp=[] # set of Vs from simulations
    print "Doing ",NumSims," simulations"
    for k in range(NumSims):
        counter+=1
        if counter==50:
            print k+1
            counter=0
        Dirp=[]
# get a set of N1 fisher distributed vectors with k1, calculate fisher stats
        for i in range(pars_1["n"]):
            Dirp.append(fshdev(pars_1["k"]))
        pars_p1=fisher_mean(Dirp)
# get a set of N2 fisher distributed vectors with k2, calculate fisher stats
        Dirp=[]
        for i in range(pars_2["n"]):
            Dirp.append(fshdev(pars_2["k"]))
        pars_p2=fisher_mean(Dirp)
# get the V for these
        Vk=vfunc(pars_p1,pars_p2)
        Vp.append(Vk)
#
# sort the Vs, get Vcrit (95th one)
#
    Vp.sort()
    k=int(.95*NumSims)
    return V,Vp[k]


def dimap(D,I):
    """
    FUNCTION TO MAP DECLINATION, INCLINATIONS INTO EQUAL AREA PROJECTION, X,Y

    Usage:     dimap(D, I)
    Argin:     Declination (float) and Inclination (float)

    """
### DEFINE FUNCTION VARIABLES
    XY=[0.,0.]                                     # initialize equal area projection x,y

### GET CARTESIAN COMPONENTS OF INPUT DIRECTION
    X=dir2cart([D,I,1.])

### CHECK IF Z = 1 AND ABORT
    if X[2] ==1.0: return XY                       # return [0,0]

### TAKE THE ABSOLUTE VALUE OF Z
    if X[2]<0:X[2]=-X[2]                           # this only works on lower hemisphere projections

### CALCULATE THE X,Y COORDINATES FOR THE EQUAL AREA PROJECTION
    R=numpy.sqrt( 1.-X[2])/(numpy.sqrt(X[0]**2+X[1]**2)) # from Collinson 1983
    XY[1],XY[0]=X[0]*R,X[1]*R

### RETURN XY[X,Y]
    return XY

def dimap_V(D,I):
    """
    FUNCTION TO MAP DECLINATION, INCLINATIONS INTO EQUAL AREA PROJECTION, X,Y

    Usage:     dimap_V(D, I)
        D and I are both numpy arrays

    """
### GET CARTESIAN COMPONENTS OF INPUT DIRECTION
    DI=numpy.array([D,I]).transpose() #
    X=dir2cart(DI).transpose()
### CALCULATE THE X,Y COORDINATES FOR THE EQUAL AREA PROJECTION
    R=numpy.sqrt( 1.-abs(X[2]))/(numpy.sqrt(X[0]**2+X[1]**2)) # from Collinson 1983
    XY=numpy.array([X[1]*R,X[0]*R]).transpose()

### RETURN XY[X,Y]
    return XY

def getmeths(method_type):
    """
    returns MagIC  method codes available for a given type
    """
    meths=[]
    if method_type=='GM':
        meths.append('GM-PMAG-APWP')
        meths.append('GM-ARAR')
        meths.append('GM-ARAR-AP')
        meths.append('GM-ARAR-II')
        meths.append('GM-ARAR-NI')
        meths.append('GM-ARAR-TF')
        meths.append('GM-CC-ARCH')
        meths.append('GM-CC-ARCHMAG')
        meths.append('GM-C14')
        meths.append('GM-FOSSIL')
        meths.append('GM-FT')
        meths.append('GM-INT-L')
        meths.append('GM-INT-S')
        meths.append('GM-ISO')
        meths.append('GM-KAR')
        meths.append('GM-PMAG-ANOM')
        meths.append('GM-PMAG-POL')
        meths.append('GM-PBPB')
        meths.append('GM-RATH')
        meths.append('GM-RBSR')
        meths.append('GM-RBSR-I')
        meths.append('GM-RBSR-MA')
        meths.append('GM-SMND')
        meths.append('GM-SMND-I')
        meths.append('GM-SMND-MA')
        meths.append('GM-CC-STRAT')
        meths.append('GM-LUM-TH')
        meths.append('GM-UPA')
        meths.append('GM-UPB')
        meths.append('GM-UTH')
        meths.append('GM-UTHHE')
    else: pass
    return meths

def first_up(ofile,Rec,file_type):
    """
    writes the header for a MagIC template file
    """
    keylist=[]
    pmag_out=open(ofile,'a')
    outstring="tab \t"+file_type+"\n"
    pmag_out.write(outstring)
    keystring=""
    for key in Rec.keys():
        keystring=keystring+'\t'+key
        keylist.append(key)
    keystring=keystring + '\n'
    pmag_out.write(keystring[1:])
    pmag_out.close()
    return keylist

def average_int(data,keybase,outkey): # returns dictionary with average intensities from list of arbitrary dictinaries.
    Ints,DataRec=[],{}
    for r in data:Ints.append(float(r[keybase+'_int']))
    if len(Ints)>1:
        b,sig=gausspars(Ints)
        sigperc=100.*sig/b
        DataRec[outkey+"_int_sigma"]='%8.3e '% (sig)
        DataRec[outkey+"_int_sigma_perc"]='%5.1f '%(sigperc)
    else: # if only one, just copy over specimen data
        b=Ints[0]
        DataRec[outkey+"_int_sigma"]=''
        DataRec[outkey+"_int_sigma_perc"]=''
    DataRec[outkey+"_int"]='%8.3e '%(b)
    DataRec[outkey+"_int_n"]='%i '% (len(data))
    return DataRec

def get_age(Rec,sitekey,keybase,Ages,DefaultAge):
    """
    finds the age record for a given site
    """
    site=Rec[sitekey]
    gotone=0
    if len(Ages)>0:
        for agerec in Ages:
            if agerec["er_site_name"]==site:
                if "age" in agerec.keys() and agerec["age"]!="":
                    Rec[keybase+"age"]=agerec["age"]
                    gotone=1
                if "age_unit" in agerec.keys(): Rec[keybase+"age_unit"]=agerec["age_unit"]
                if "age_sigma" in agerec.keys(): Rec[keybase+"age_sigma"]=agerec["age_sigma"]
    if gotone==0 and len(DefaultAge)>1:
        sigma=0.5*(float(DefaultAge[1])-float(DefaultAge[0]))
        age=float(DefaultAge[0])+sigma
        Rec[keybase+"age"]= '%10.4e'%(age)
        Rec[keybase+"age_sigma"]= '%10.4e'%(sigma)
        Rec[keybase+"age_unit"]=DefaultAge[2]
    return Rec
#
def adjust_ages(AgesIn):
    """
    Function to adjust ages to a common age_unit
    """
# get a list of age_units first
    age_units,AgesOut,factors,factor,maxunit,age_unit=[],[],[],1,1,"Ma"
    for agerec in AgesIn:
        if agerec[1] not in age_units:
            age_units.append(agerec[1])
            if agerec[1]=="Ga":
                factors.append(1e9)
                maxunit,age_unit,factor=1e9,"Ga",1e9
            if agerec[1]=="Ma":
                if maxunit==1:maxunit,age_unt,factor=1e6,"Ma",1e6
                factors.append(1e6)
            if agerec[1]=="Ka":
                factors.append(1e3)
                if maxunit==1:maxunit,age_unit,factor=1e3,"Ka",1e3
            if "Years" in agerec[1].split():factors.append(1)
    if len(age_units)==1: # all ages are of same type
        for agerec in AgesIn:
            AgesOut.append(agerec[0])
    elif len(age_units)>1:
        for agerec in AgesIn:  # normalize all to largest age unit
            if agerec[1]=="Ga":AgesOut.append(agerec[0]*1e9/factor)
            if agerec[1]=="Ma":AgesOut.append(agerec[0]*1e6/factor)
            if agerec[1]=="Ka":AgesOut.append(agerec[0]*1e3/factor)
            if "Years" in agerec[1].split():
                if agerec[1]=="Years BP":AgesOut.append(agerec[0]/factor)
                if agerec[1]=="Years Cal BP":AgesOut.append(agerec[0]/factor)
                if agerec[1]=="Years AD (+/-)":AgesOut.append((1950-agerec[0])/factor) # convert to years BP first
                if agerec[1]=="Years Cal AD (+/-)":AgesOut.append((1950-agerec[0])/factor)
    return AgesOut,age_unit
#
def gaussdev(mean,sigma):
    """
    returns a number randomly drawn from a gaussian distribution with the given mean, sigma
    """
    return random.normal(mean,sigma) # return gaussian deviate
#
def get_unf(N):
    """
    Called with get_unf(N).
 subroutine to retrieve N uniformly distributed directions
 using the way described in Fisher et al. (1987).
    """
#
# get uniform directions  [dec,inc]
    z=random.uniform(-1.,1.,size=N)
    t=random.uniform(0.,360.,size=N) # decs
    i=numpy.arcsin(z)*180./numpy.pi # incs
    return numpy.array([t,i]).transpose()

#def get_unf(N): #Jeff's way
    """
     subroutine to retrieve N uniformly distributed directions
    """
#    nmax,k=5550,66   # initialize stuff for uniform distribution
#    di,xn,yn,zn=[],[],[],[]
##
## get uniform direcctions (x,y,z)
#    for  i in range(1,k):
#        m = int(2*float(k)*numpy.sin(numpy.pi*float(i)/float(k)))
#        for j in range(m):
#            x=numpy.sin(numpy.pi*float(i)/float(k))*numpy.cos(2.*numpy.pi*float(j)/float(m))
#            y=numpy.sin(numpy.pi*float(i)/float(k))*numpy.sin(2.*numpy.pi*float(j)/float(m))
#            z=numpy.cos(numpy.pi*float(i)/float(k))
#            r=numpy.sqrt(x**2+y**2+z**2)
#            xn.append(x/r)
#            yn.append(y/r)
#            zn.append(z/r)
##
## select N random phi/theta from unf dist.
#
#    while len(di)<N:
#        ind=random.randint(0,len(xn)-1)
#        dir=cart2dir((xn[ind],yn[ind],zn[ind]))
#        di.append([dir[0],dir[1]])
#    return di
##
def s2a(s):
    """
     convert 6 element "s" list to 3,3 a matrix (see Tauxe 1998)
    """
    a=numpy.zeros((3,3,),'f') # make the a matrix
    for i in range(3):
        a[i][i]=s[i]
    a[0][1],a[1][0]=s[3],s[3]
    a[1][2],a[2][1]=s[4],s[4]
    a[0][2],a[2][0]=s[5],s[5]
    return a
#
def a2s(a):
    """
     convert 3,3 a matrix to 6 element "s" list  (see Tauxe 1998)
    """
    s=numpy.zeros((6,),'f') # make the a matrix
    for i in range(3):
        s[i]=a[i][i]
    s[3]=a[0][1]
    s[4]=a[1][2]
    s[5]=a[0][2]
    return s

def doseigs(s):
    """
    convert s format for eigenvalues and eigenvectors
    """
#
    A=s2a(s) # convert s to a (see Tauxe 1998)
    tau,V=tauV(A) # convert to eigenvalues (t), eigenvectors (V)
    Vdirs=[]
    for v in V: # convert from cartesian to direction
        Vdir= cart2dir(v)
        if Vdir[1]<0:
            Vdir[1]=-Vdir[1]
            Vdir[0]=(Vdir[0]+180.)%360.
        Vdirs.append([Vdir[0],Vdir[1]])
    return tau,Vdirs
#
#
def doeigs_s(tau,Vdirs):
    """
     get elements of s from eigenvaulues - note that this is very unstable
    """
#
    V=[]
    t=numpy.zeros((3,3,),'f') # initialize the tau diagonal matrix
    for j in range(3): t[j][j]=tau[j] # diagonalize tau
    for k in range(3):
        V.append(dir2cart([Vdirs[k][0],Vdirs[k][1],1.0]))
    V=numpy.transpose(V)
    tmp=numpy.dot(V,t)
    chi=numpy.dot(tmp,numpy.transpose(V))
    return a2s(chi)
#
#
def fcalc(col,row):
    """
  looks up f from ftables F(row,col), where row is number of degrees of freedom - this is 95% confidence (p=0.05)
    """
#
    if row>200:row=200
    if col>20:col=20
    ftest=numpy.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
[1, 161.469, 199.493, 215.737, 224.5, 230.066, 234.001, 236.772, 238.949, 240.496, 241.838, 242.968, 243.88, 244.798, 245.26, 245.956, 246.422, 246.89, 247.36, 247.596, 248.068],
[2, 18.5128, 18.9995, 19.1642, 19.2467, 19.2969, 19.3299, 19.3536, 19.371, 19.3852, 19.3963, 19.4043, 19.4122, 19.4186, 19.425, 19.4297, 19.4329, 19.4377, 19.4409, 19.4425, 19.4457],
[3, 10.1278, 9.5522, 9.2767, 9.1173, 9.0133, 8.9408, 8.8868, 8.8452, 8.8124, 8.7857, 8.7635, 8.7446, 8.7287, 8.715, 8.7028, 8.6923, 8.683, 8.6745, 8.667, 8.6602],
[4, 7.7087, 6.9444, 6.5915, 6.3882, 6.2561, 6.1631, 6.0943, 6.0411, 5.9988, 5.9644, 5.9359, 5.9117, 5.8912, 5.8733, 5.8578, 5.844, 5.8319, 5.8211, 5.8113, 5.8025],
[5, 6.608, 5.7861, 5.4095, 5.1922, 5.0503, 4.9503, 4.8759, 4.8184, 4.7725, 4.735, 4.7039, 4.6777, 4.6552, 4.6358, 4.6187, 4.6038, 4.5904, 4.5785, 4.5679, 4.5581],
[6, 5.9874, 5.1433, 4.757, 4.5337, 4.3874, 4.2838, 4.2067, 4.1468, 4.099, 4.06, 4.0275, 3.9999, 3.9764, 3.956, 3.9381, 3.9223, 3.9083, 3.8957, 3.8844, 3.8742],
[7, 5.5914, 4.7374, 4.3469, 4.1204, 3.9715, 3.866, 3.787, 3.7257, 3.6767, 3.6366, 3.603, 3.5747, 3.5504, 3.5292, 3.5107, 3.4944, 3.4799, 3.4669, 3.4552, 3.4445],
[8, 5.3177, 4.459, 4.0662, 3.8378, 3.6875, 3.5806, 3.5004, 3.4381, 3.3881, 3.3472, 3.313, 3.2839, 3.259, 3.2374, 3.2184, 3.2017, 3.1867, 3.1733, 3.1613, 3.1503],
[9, 5.1174, 4.2565, 3.8626, 3.6331, 3.4817, 3.3738, 3.2928, 3.2296, 3.1789, 3.1373, 3.1025, 3.0729, 3.0475, 3.0255, 3.0061, 2.989, 2.9737, 2.96, 2.9476, 2.9365],
[10, 4.9647, 4.1028, 3.7083, 3.4781, 3.3258, 3.2171, 3.1355, 3.0717, 3.0204, 2.9782, 2.9429, 2.913, 2.8872, 2.8648, 2.845, 2.8276, 2.812, 2.7981, 2.7855, 2.774],
[11, 4.8443, 3.9823, 3.5875, 3.3567, 3.2039, 3.0946, 3.0123, 2.948, 2.8962, 2.8536, 2.8179, 2.7876, 2.7614, 2.7386, 2.7186, 2.7009, 2.6851, 2.6709, 2.6581, 2.6464],
[12, 4.7472, 3.8853, 3.4903, 3.2592, 3.1059, 2.9961, 2.9134, 2.8486, 2.7964, 2.7534, 2.7173, 2.6866, 2.6602, 2.6371, 2.6169, 2.5989, 2.5828, 2.5684, 2.5554, 2.5436],
[13, 4.6672, 3.8055, 3.4106, 3.1791, 3.0255, 2.9153, 2.8321, 2.7669, 2.7144, 2.6711, 2.6347, 2.6037, 2.5769, 2.5536, 2.5331, 2.5149, 2.4987, 2.4841, 2.4709, 2.4589],
[14, 4.6001, 3.7389, 3.3439, 3.1122, 2.9582, 2.8477, 2.7642, 2.6987, 2.6458, 2.6021, 2.5655, 2.5343, 2.5073, 2.4837, 2.463, 2.4446, 2.4282, 2.4134, 2.4, 2.3879],
[15, 4.543, 3.6824, 3.2874, 3.0555, 2.9013, 2.7905, 2.7066, 2.6408, 2.5877, 2.5437, 2.5068, 2.4753, 2.4481, 2.4244, 2.4034, 2.3849, 2.3683, 2.3533, 2.3398, 2.3275],
[16, 4.494, 3.6337, 3.2389, 3.0069, 2.8524, 2.7413, 2.6572, 2.5911, 2.5377, 2.4935, 2.4564, 2.4247, 2.3973, 2.3733, 2.3522, 2.3335, 2.3167, 2.3016, 2.288, 2.2756],
[17, 4.4513, 3.5916, 3.1968, 2.9647, 2.81, 2.6987, 2.6143, 2.548, 2.4943, 2.4499, 2.4126, 2.3807, 2.3531, 2.329, 2.3077, 2.2888, 2.2719, 2.2567, 2.2429, 2.2303],
[18, 4.4139, 3.5546, 3.1599, 2.9278, 2.7729, 2.6613, 2.5767, 2.5102, 2.4563, 2.4117, 2.3742, 2.3421, 2.3143, 2.29, 2.2686, 2.2496, 2.2325, 2.2172, 2.2033, 2.1906],
[19, 4.3808, 3.5219, 3.1274, 2.8951, 2.7401, 2.6283, 2.5435, 2.4768, 2.4227, 2.378, 2.3402, 2.308, 2.28, 2.2556, 2.2341, 2.2149, 2.1977, 2.1823, 2.1683, 2.1555],
[20, 4.3512, 3.4928, 3.0984, 2.8661, 2.7109, 2.599, 2.514, 2.4471, 2.3928, 2.3479, 2.31, 2.2776, 2.2495, 2.2249, 2.2033, 2.184, 2.1667, 2.1511, 2.137, 2.1242],
[21, 4.3248, 3.4668, 3.0725, 2.8401, 2.6848, 2.5727, 2.4876, 2.4205, 2.3661, 2.3209, 2.2829, 2.2504, 2.2222, 2.1975, 2.1757, 2.1563, 2.1389, 2.1232, 2.109, 2.096],
[22, 4.3009, 3.4434, 3.0492, 2.8167, 2.6613, 2.5491, 2.4638, 2.3965, 2.3419, 2.2967, 2.2585, 2.2258, 2.1975, 2.1727, 2.1508, 2.1313, 2.1138, 2.098, 2.0837, 2.0707],
[23, 4.2794, 3.4221, 3.028, 2.7955, 2.64, 2.5276, 2.4422, 2.3748, 2.3201, 2.2747, 2.2364, 2.2036, 2.1752, 2.1503, 2.1282, 2.1086, 2.091, 2.0751, 2.0608, 2.0476],
[24, 4.2597, 3.4029, 3.0088, 2.7763, 2.6206, 2.5082, 2.4226, 2.3551, 2.3003, 2.2547, 2.2163, 2.1834, 2.1548, 2.1298, 2.1077, 2.088, 2.0703, 2.0543, 2.0399, 2.0267],
[25, 4.2417, 3.3852, 2.9913, 2.7587, 2.603, 2.4904, 2.4047, 2.3371, 2.2821, 2.2365, 2.1979, 2.1649, 2.1362, 2.1111, 2.0889, 2.0691, 2.0513, 2.0353, 2.0207, 2.0075],
[26, 4.2252, 3.369, 2.9752, 2.7426, 2.5868, 2.4741, 2.3883, 2.3205, 2.2655, 2.2197, 2.1811, 2.1479, 2.1192, 2.094, 2.0716, 2.0518, 2.0339, 2.0178, 2.0032, 1.9898],
[27, 4.21, 3.3542, 2.9603, 2.7277, 2.5719, 2.4591, 2.3732, 2.3053, 2.2501, 2.2043, 2.1656, 2.1323, 2.1035, 2.0782, 2.0558, 2.0358, 2.0179, 2.0017, 1.987, 1.9736],
[28, 4.196, 3.3404, 2.9467, 2.7141, 2.5581, 2.4453, 2.3592, 2.2913, 2.236, 2.1901, 2.1512, 2.1179, 2.0889, 2.0636, 2.0411, 2.021, 2.0031, 1.9868, 1.972, 1.9586],
[29, 4.1829, 3.3276, 2.9341, 2.7014, 2.5454, 2.4324, 2.3463, 2.2783, 2.2229, 2.1768, 2.1379, 2.1045, 2.0755, 2.05, 2.0275, 2.0074, 1.9893, 1.973, 1.9582, 1.9446],
[30, 4.1709, 3.3158, 2.9223, 2.6896, 2.5335, 2.4205, 2.3343, 2.2662, 2.2107, 2.1646, 2.1255, 2.0921, 2.0629, 2.0374, 2.0148, 1.9946, 1.9765, 1.9601, 1.9452, 1.9317],
[31, 4.1597, 3.3048, 2.9113, 2.6787, 2.5225, 2.4094, 2.3232, 2.2549, 2.1994, 2.1531, 2.1141, 2.0805, 2.0513, 2.0257, 2.003, 1.9828, 1.9646, 1.9481, 1.9332, 1.9196],
[32, 4.1491, 3.2945, 2.9011, 2.6684, 2.5123, 2.3991, 2.3127, 2.2444, 2.1888, 2.1425, 2.1033, 2.0697, 2.0404, 2.0147, 1.992, 1.9717, 1.9534, 1.9369, 1.9219, 1.9083],
[33, 4.1392, 3.2849, 2.8915, 2.6589, 2.5027, 2.3894, 2.303, 2.2346, 2.1789, 2.1325, 2.0933, 2.0596, 2.0302, 2.0045, 1.9817, 1.9613, 1.943, 1.9264, 1.9114, 1.8977],
[34, 4.13, 3.2759, 2.8826, 2.6499, 2.4936, 2.3803, 2.2938, 2.2253, 2.1696, 2.1231, 2.0838, 2.05, 2.0207, 1.9949, 1.972, 1.9516, 1.9332, 1.9166, 1.9015, 1.8877],
[35, 4.1214, 3.2674, 2.8742, 2.6415, 2.4851, 2.3718, 2.2852, 2.2167, 2.1608, 2.1143, 2.0749, 2.0411, 2.0117, 1.9858, 1.9629, 1.9424, 1.924, 1.9073, 1.8922, 1.8784],
[36, 4.1132, 3.2594, 2.8663, 2.6335, 2.4771, 2.3637, 2.2771, 2.2085, 2.1526, 2.1061, 2.0666, 2.0327, 2.0032, 1.9773, 1.9543, 1.9338, 1.9153, 1.8986, 1.8834, 1.8696],
[37, 4.1055, 3.2519, 2.8588, 2.6261, 2.4696, 2.3562, 2.2695, 2.2008, 2.1449, 2.0982, 2.0587, 2.0248, 1.9952, 1.9692, 1.9462, 1.9256, 1.9071, 1.8904, 1.8752, 1.8613],
[38, 4.0981, 3.2448, 2.8517, 2.619, 2.4625, 2.349, 2.2623, 2.1935, 2.1375, 2.0909, 2.0513, 2.0173, 1.9877, 1.9617, 1.9386, 1.9179, 1.8994, 1.8826, 1.8673, 1.8534],
[39, 4.0913, 3.2381, 2.8451, 2.6123, 2.4558, 2.3422, 2.2555, 2.1867, 2.1306, 2.0839, 2.0442, 2.0102, 1.9805, 1.9545, 1.9313, 1.9107, 1.8921, 1.8752, 1.8599, 1.8459],
[40, 4.0848, 3.2317, 2.8388, 2.606, 2.4495, 2.3359, 2.249, 2.1802, 2.124, 2.0773, 2.0376, 2.0035, 1.9738, 1.9476, 1.9245, 1.9038, 1.8851, 1.8682, 1.8529, 1.8389],
[41, 4.0786, 3.2257, 2.8328, 2.6, 2.4434, 2.3298, 2.2429, 2.174, 2.1178, 2.071, 2.0312, 1.9971, 1.9673, 1.9412, 1.9179, 1.8972, 1.8785, 1.8616, 1.8462, 1.8321],
[42, 4.0727, 3.2199, 2.8271, 2.5943, 2.4377, 2.324, 2.2371, 2.1681, 2.1119, 2.065, 2.0252, 1.991, 1.9612, 1.935, 1.9118, 1.8909, 1.8722, 1.8553, 1.8399, 1.8258],
[43, 4.067, 3.2145, 2.8216, 2.5888, 2.4322, 2.3185, 2.2315, 2.1625, 2.1062, 2.0593, 2.0195, 1.9852, 1.9554, 1.9292, 1.9059, 1.885, 1.8663, 1.8493, 1.8338, 1.8197],
[44, 4.0617, 3.2093, 2.8165, 2.5837, 2.4271, 2.3133, 2.2262, 2.1572, 2.1009, 2.0539, 2.014, 1.9797, 1.9499, 1.9236, 1.9002, 1.8794, 1.8606, 1.8436, 1.8281, 1.8139],
[45, 4.0566, 3.2043, 2.8115, 2.5787, 2.4221, 2.3083, 2.2212, 2.1521, 2.0958, 2.0487, 2.0088, 1.9745, 1.9446, 1.9182, 1.8949, 1.874, 1.8551, 1.8381, 1.8226, 1.8084],
[46, 4.0518, 3.1996, 2.8068, 2.574, 2.4174, 2.3035, 2.2164, 2.1473, 2.0909, 2.0438, 2.0039, 1.9695, 1.9395, 1.9132, 1.8898, 1.8688, 1.85, 1.8329, 1.8173, 1.8031],
[47, 4.0471, 3.1951, 2.8024, 2.5695, 2.4128, 2.299, 2.2118, 2.1427, 2.0862, 2.0391, 1.9991, 1.9647, 1.9347, 1.9083, 1.8849, 1.8639, 1.845, 1.8279, 1.8123, 1.798],
[48, 4.0426, 3.1907, 2.7981, 2.5653, 2.4085, 2.2946, 2.2074, 2.1382, 2.0817, 2.0346, 1.9946, 1.9601, 1.9301, 1.9037, 1.8802, 1.8592, 1.8402, 1.8231, 1.8075, 1.7932],
[49, 4.0384, 3.1866, 2.7939, 2.5611, 2.4044, 2.2904, 2.2032, 2.134, 2.0774, 2.0303, 1.9902, 1.9558, 1.9257, 1.8992, 1.8757, 1.8547, 1.8357, 1.8185, 1.8029, 1.7886],
[50, 4.0343, 3.1826, 2.79, 2.5572, 2.4004, 2.2864, 2.1992, 2.1299, 2.0734, 2.0261, 1.9861, 1.9515, 1.9214, 1.8949, 1.8714, 1.8503, 1.8313, 1.8141, 1.7985, 1.7841],
[51, 4.0303, 3.1788, 2.7862, 2.5534, 2.3966, 2.2826, 2.1953, 2.126, 2.0694, 2.0222, 1.982, 1.9475, 1.9174, 1.8908, 1.8673, 1.8462, 1.8272, 1.8099, 1.7942, 1.7798],
[52, 4.0266, 3.1752, 2.7826, 2.5498, 2.3929, 2.2789, 2.1916, 2.1223, 2.0656, 2.0184, 1.9782, 1.9436, 1.9134, 1.8869, 1.8633, 1.8422, 1.8231, 1.8059, 1.7901, 1.7758],
[53, 4.023, 3.1716, 2.7791, 2.5463, 2.3894, 2.2754, 2.1881, 2.1187, 2.062, 2.0147, 1.9745, 1.9399, 1.9097, 1.8831, 1.8595, 1.8383, 1.8193, 1.802, 1.7862, 1.7718],
[54, 4.0196, 3.1683, 2.7757, 2.5429, 2.3861, 2.272, 2.1846, 2.1152, 2.0585, 2.0112, 1.971, 1.9363, 1.9061, 1.8795, 1.8558, 1.8346, 1.8155, 1.7982, 1.7825, 1.768],
[55, 4.0162, 3.165, 2.7725, 2.5397, 2.3828, 2.2687, 2.1813, 2.1119, 2.0552, 2.0078, 1.9676, 1.9329, 1.9026, 1.876, 1.8523, 1.8311, 1.812, 1.7946, 1.7788, 1.7644],
[56, 4.0129, 3.1618, 2.7694, 2.5366, 2.3797, 2.2656, 2.1781, 2.1087, 2.0519, 2.0045, 1.9642, 1.9296, 1.8993, 1.8726, 1.8489, 1.8276, 1.8085, 1.7912, 1.7753, 1.7608],
[57, 4.0099, 3.1589, 2.7665, 2.5336, 2.3767, 2.2625, 2.1751, 2.1056, 2.0488, 2.0014, 1.9611, 1.9264, 1.896, 1.8693, 1.8456, 1.8244, 1.8052, 1.7878, 1.772, 1.7575],
[58, 4.0069, 3.1559, 2.7635, 2.5307, 2.3738, 2.2596, 2.1721, 2.1026, 2.0458, 1.9983, 1.958, 1.9233, 1.8929, 1.8662, 1.8424, 1.8212, 1.802, 1.7846, 1.7687, 1.7542],
[59, 4.0039, 3.1531, 2.7608, 2.5279, 2.371, 2.2568, 2.1693, 2.0997, 2.0429, 1.9954, 1.9551, 1.9203, 1.8899, 1.8632, 1.8394, 1.8181, 1.7989, 1.7815, 1.7656, 1.751],
[60, 4.0012, 3.1504, 2.7581, 2.5252, 2.3683, 2.254, 2.1665, 2.097, 2.0401, 1.9926, 1.9522, 1.9174, 1.887, 1.8603, 1.8364, 1.8151, 1.7959, 1.7784, 1.7625, 1.748],
[61, 3.9985, 3.1478, 2.7555, 2.5226, 2.3657, 2.2514, 2.1639, 2.0943, 2.0374, 1.9899, 1.9495, 1.9146, 1.8842, 1.8574, 1.8336, 1.8122, 1.793, 1.7755, 1.7596, 1.745],
[62, 3.9959, 3.1453, 2.753, 2.5201, 2.3631, 2.2489, 2.1613, 2.0917, 2.0348, 1.9872, 1.9468, 1.9119, 1.8815, 1.8547, 1.8308, 1.8095, 1.7902, 1.7727, 1.7568, 1.7422],
[63, 3.9934, 3.1428, 2.7506, 2.5176, 2.3607, 2.2464, 2.1588, 2.0892, 2.0322, 1.9847, 1.9442, 1.9093, 1.8789, 1.852, 1.8282, 1.8068, 1.7875, 1.77, 1.754, 1.7394],
[64, 3.9909, 3.1404, 2.7482, 2.5153, 2.3583, 2.244, 2.1564, 2.0868, 2.0298, 1.9822, 1.9417, 1.9068, 1.8763, 1.8495, 1.8256, 1.8042, 1.7849, 1.7673, 1.7514, 1.7368],
[65, 3.9885, 3.1381, 2.7459, 2.513, 2.356, 2.2417, 2.1541, 2.0844, 2.0274, 1.9798, 1.9393, 1.9044, 1.8739, 1.847, 1.8231, 1.8017, 1.7823, 1.7648, 1.7488, 1.7342],
[66, 3.9862, 3.1359, 2.7437, 2.5108, 2.3538, 2.2395, 2.1518, 2.0821, 2.0251, 1.9775, 1.937, 1.902, 1.8715, 1.8446, 1.8207, 1.7992, 1.7799, 1.7623, 1.7463, 1.7316],
[67, 3.9841, 3.1338, 2.7416, 2.5087, 2.3516, 2.2373, 2.1497, 2.0799, 2.0229, 1.9752, 1.9347, 1.8997, 1.8692, 1.8423, 1.8183, 1.7968, 1.7775, 1.7599, 1.7439, 1.7292],
[68, 3.9819, 3.1317, 2.7395, 2.5066, 2.3496, 2.2352, 2.1475, 2.0778, 2.0207, 1.973, 1.9325, 1.8975, 1.867, 1.84, 1.816, 1.7945, 1.7752, 1.7576, 1.7415, 1.7268],
[69, 3.9798, 3.1297, 2.7375, 2.5046, 2.3475, 2.2332, 2.1455, 2.0757, 2.0186, 1.9709, 1.9303, 1.8954, 1.8648, 1.8378, 1.8138, 1.7923, 1.7729, 1.7553, 1.7393, 1.7246],
[70, 3.9778, 3.1277, 2.7355, 2.5027, 2.3456, 2.2312, 2.1435, 2.0737, 2.0166, 1.9689, 1.9283, 1.8932, 1.8627, 1.8357, 1.8117, 1.7902, 1.7707, 1.7531, 1.7371, 1.7223],
[71, 3.9758, 3.1258, 2.7336, 2.5007, 2.3437, 2.2293, 2.1415, 2.0717, 2.0146, 1.9669, 1.9263, 1.8912, 1.8606, 1.8336, 1.8096, 1.7881, 1.7686, 1.751, 1.7349, 1.7202],
[72, 3.9739, 3.1239, 2.7318, 2.4989, 2.3418, 2.2274, 2.1397, 2.0698, 2.0127, 1.9649, 1.9243, 1.8892, 1.8586, 1.8316, 1.8076, 1.786, 1.7666, 1.7489, 1.7328, 1.7181],
[73, 3.9721, 3.1221, 2.73, 2.4971, 2.34, 2.2256, 2.1378, 2.068, 2.0108, 1.9631, 1.9224, 1.8873, 1.8567, 1.8297, 1.8056, 1.784, 1.7646, 1.7469, 1.7308, 1.716],
[74, 3.9703, 3.1204, 2.7283, 2.4954, 2.3383, 2.2238, 2.1361, 2.0662, 2.009, 1.9612, 1.9205, 1.8854, 1.8548, 1.8278, 1.8037, 1.7821, 1.7626, 1.7449, 1.7288, 1.714],
[75, 3.9685, 3.1186, 2.7266, 2.4937, 2.3366, 2.2221, 2.1343, 2.0645, 2.0073, 1.9595, 1.9188, 1.8836, 1.853, 1.8259, 1.8018, 1.7802, 1.7607, 1.7431, 1.7269, 1.7121],
[76, 3.9668, 3.117, 2.7249, 2.4921, 2.3349, 2.2204, 2.1326, 2.0627, 2.0055, 1.9577, 1.917, 1.8819, 1.8512, 1.8241, 1.8, 1.7784, 1.7589, 1.7412, 1.725, 1.7102],
[77, 3.9651, 3.1154, 2.7233, 2.4904, 2.3333, 2.2188, 2.131, 2.0611, 2.0039, 1.956, 1.9153, 1.8801, 1.8494, 1.8223, 1.7982, 1.7766, 1.7571, 1.7394, 1.7232, 1.7084],
[78, 3.9635, 3.1138, 2.7218, 2.4889, 2.3318, 2.2172, 2.1294, 2.0595, 2.0022, 1.9544, 1.9136, 1.8785, 1.8478, 1.8206, 1.7965, 1.7749, 1.7554, 1.7376, 1.7214, 1.7066],
[79, 3.9619, 3.1123, 2.7203, 2.4874, 2.3302, 2.2157, 2.1279, 2.0579, 2.0006, 1.9528, 1.912, 1.8769, 1.8461, 1.819, 1.7948, 1.7732, 1.7537, 1.7359, 1.7197, 1.7048],
[80, 3.9604, 3.1107, 2.7188, 2.4859, 2.3287, 2.2142, 2.1263, 2.0564, 1.9991, 1.9512, 1.9105, 1.8753, 1.8445, 1.8174, 1.7932, 1.7716, 1.752, 1.7342, 1.718, 1.7032],
[81, 3.9589, 3.1093, 2.7173, 2.4845, 2.3273, 2.2127, 2.1248, 2.0549, 1.9976, 1.9497, 1.9089, 1.8737, 1.8429, 1.8158, 1.7916, 1.77, 1.7504, 1.7326, 1.7164, 1.7015],
[82, 3.9574, 3.1079, 2.716, 2.483, 2.3258, 2.2113, 2.1234, 2.0534, 1.9962, 1.9482, 1.9074, 1.8722, 1.8414, 1.8143, 1.7901, 1.7684, 1.7488, 1.731, 1.7148, 1.6999],
[83, 3.956, 3.1065, 2.7146, 2.4817, 2.3245, 2.2099, 2.122, 2.052, 1.9947, 1.9468, 1.906, 1.8707, 1.8399, 1.8127, 1.7886, 1.7669, 1.7473, 1.7295, 1.7132, 1.6983],
[84, 3.9546, 3.1051, 2.7132, 2.4803, 2.3231, 2.2086, 2.1206, 2.0506, 1.9933, 1.9454, 1.9045, 1.8693, 1.8385, 1.8113, 1.7871, 1.7654, 1.7458, 1.728, 1.7117, 1.6968],
[85, 3.9532, 3.1039, 2.7119, 2.479, 2.3218, 2.2072, 2.1193, 2.0493, 1.9919, 1.944, 1.9031, 1.8679, 1.8371, 1.8099, 1.7856, 1.7639, 1.7443, 1.7265, 1.7102, 1.6953],
[86, 3.9519, 3.1026, 2.7106, 2.4777, 2.3205, 2.2059, 2.118, 2.048, 1.9906, 1.9426, 1.9018, 1.8665, 1.8357, 1.8085, 1.7842, 1.7625, 1.7429, 1.725, 1.7088, 1.6938],
[87, 3.9506, 3.1013, 2.7094, 2.4765, 2.3193, 2.2047, 2.1167, 2.0467, 1.9893, 1.9413, 1.9005, 1.8652, 1.8343, 1.8071, 1.7829, 1.7611, 1.7415, 1.7236, 1.7073, 1.6924],
[88, 3.9493, 3.1001, 2.7082, 2.4753, 2.318, 2.2034, 2.1155, 2.0454, 1.9881, 1.94, 1.8992, 1.8639, 1.833, 1.8058, 1.7815, 1.7598, 1.7401, 1.7223, 1.706, 1.691],
[89, 3.9481, 3.0988, 2.707, 2.4741, 2.3169, 2.2022, 2.1143, 2.0442, 1.9868, 1.9388, 1.8979, 1.8626, 1.8317, 1.8045, 1.7802, 1.7584, 1.7388, 1.7209, 1.7046, 1.6896],
[90, 3.9469, 3.0977, 2.7058, 2.4729, 2.3157, 2.2011, 2.1131, 2.043, 1.9856, 1.9376, 1.8967, 1.8613, 1.8305, 1.8032, 1.7789, 1.7571, 1.7375, 1.7196, 1.7033, 1.6883],
[91, 3.9457, 3.0965, 2.7047, 2.4718, 2.3146, 2.1999, 2.1119, 2.0418, 1.9844, 1.9364, 1.8955, 1.8601, 1.8292, 1.802, 1.7777, 1.7559, 1.7362, 1.7183, 1.702, 1.687],
[92, 3.9446, 3.0955, 2.7036, 2.4707, 2.3134, 2.1988, 2.1108, 2.0407, 1.9833, 1.9352, 1.8943, 1.8589, 1.828, 1.8008, 1.7764, 1.7546, 1.735, 1.717, 1.7007, 1.6857],
[93, 3.9435, 3.0944, 2.7025, 2.4696, 2.3123, 2.1977, 2.1097, 2.0395, 1.9821, 1.934, 1.8931, 1.8578, 1.8269, 1.7996, 1.7753, 1.7534, 1.7337, 1.7158, 1.6995, 1.6845],
[94, 3.9423, 3.0933, 2.7014, 2.4685, 2.3113, 2.1966, 2.1086, 2.0385, 1.981, 1.9329, 1.892, 1.8566, 1.8257, 1.7984, 1.7741, 1.7522, 1.7325, 1.7146, 1.6982, 1.6832],
[95, 3.9412, 3.0922, 2.7004, 2.4675, 2.3102, 2.1955, 2.1075, 2.0374, 1.9799, 1.9318, 1.8909, 1.8555, 1.8246, 1.7973, 1.7729, 1.7511, 1.7314, 1.7134, 1.6971, 1.682],
[96, 3.9402, 3.0912, 2.6994, 2.4665, 2.3092, 2.1945, 2.1065, 2.0363, 1.9789, 1.9308, 1.8898, 1.8544, 1.8235, 1.7961, 1.7718, 1.75, 1.7302, 1.7123, 1.6959, 1.6809],
[97, 3.9392, 3.0902, 2.6984, 2.4655, 2.3082, 2.1935, 2.1054, 2.0353, 1.9778, 1.9297, 1.8888, 1.8533, 1.8224, 1.7951, 1.7707, 1.7488, 1.7291, 1.7112, 1.6948, 1.6797],
[98, 3.9381, 3.0892, 2.6974, 2.4645, 2.3072, 2.1925, 2.1044, 2.0343, 1.9768, 1.9287, 1.8877, 1.8523, 1.8213, 1.794, 1.7696, 1.7478, 1.728, 1.71, 1.6936, 1.6786],
[99, 3.9371, 3.0882, 2.6965, 2.4636, 2.3062, 2.1916, 2.1035, 2.0333, 1.9758, 1.9277, 1.8867, 1.8513, 1.8203, 1.7929, 1.7686, 1.7467, 1.7269, 1.709, 1.6926, 1.6775],
[100, 3.9361, 3.0873, 2.6955, 2.4626, 2.3053, 2.1906, 2.1025, 2.0323, 1.9748, 1.9267, 1.8857, 1.8502, 1.8193, 1.7919, 1.7675, 1.7456, 1.7259, 1.7079, 1.6915, 1.6764],
[101, 3.9352, 3.0864, 2.6946, 2.4617, 2.3044, 2.1897, 2.1016, 2.0314, 1.9739, 1.9257, 1.8847, 1.8493, 1.8183, 1.7909, 1.7665, 1.7446, 1.7248, 1.7069, 1.6904, 1.6754],
[102, 3.9342, 3.0854, 2.6937, 2.4608, 2.3035, 2.1888, 2.1007, 2.0304, 1.9729, 1.9248, 1.8838, 1.8483, 1.8173, 1.7899, 1.7655, 1.7436, 1.7238, 1.7058, 1.6894, 1.6744],
[103, 3.9333, 3.0846, 2.6928, 2.4599, 2.3026, 2.1879, 2.0997, 2.0295, 1.972, 1.9238, 1.8828, 1.8474, 1.8163, 1.789, 1.7645, 1.7427, 1.7229, 1.7048, 1.6884, 1.6733],
[104, 3.9325, 3.0837, 2.692, 2.4591, 2.3017, 2.187, 2.0989, 2.0287, 1.9711, 1.9229, 1.8819, 1.8464, 1.8154, 1.788, 1.7636, 1.7417, 1.7219, 1.7039, 1.6874, 1.6723],
[105, 3.9316, 3.0828, 2.6912, 2.4582, 2.3009, 2.1861, 2.098, 2.0278, 1.9702, 1.922, 1.881, 1.8455, 1.8145, 1.7871, 1.7627, 1.7407, 1.7209, 1.7029, 1.6865, 1.6714],
[106, 3.9307, 3.082, 2.6903, 2.4574, 2.3, 2.1853, 2.0971, 2.0269, 1.9694, 1.9212, 1.8801, 1.8446, 1.8136, 1.7862, 1.7618, 1.7398, 1.72, 1.702, 1.6855, 1.6704],
[107, 3.9299, 3.0812, 2.6895, 2.4566, 2.2992, 2.1845, 2.0963, 2.0261, 1.9685, 1.9203, 1.8792, 1.8438, 1.8127, 1.7853, 1.7608, 1.7389, 1.7191, 1.7011, 1.6846, 1.6695],
[108, 3.929, 3.0804, 2.6887, 2.4558, 2.2984, 2.1837, 2.0955, 2.0252, 1.9677, 1.9195, 1.8784, 1.8429, 1.8118, 1.7844, 1.7599, 1.738, 1.7182, 1.7001, 1.6837, 1.6685],
[109, 3.9282, 3.0796, 2.6879, 2.455, 2.2976, 2.1828, 2.0947, 2.0244, 1.9669, 1.9186, 1.8776, 1.8421, 1.811, 1.7835, 1.7591, 1.7371, 1.7173, 1.6992, 1.6828, 1.6676],
[110, 3.9274, 3.0788, 2.6872, 2.4542, 2.2968, 2.1821, 2.0939, 2.0236, 1.9661, 1.9178, 1.8767, 1.8412, 1.8102, 1.7827, 1.7582, 1.7363, 1.7164, 1.6984, 1.6819, 1.6667],
[111, 3.9266, 3.0781, 2.6864, 2.4535, 2.2961, 2.1813, 2.0931, 2.0229, 1.9653, 1.917, 1.8759, 1.8404, 1.8093, 1.7819, 1.7574, 1.7354, 1.7156, 1.6975, 1.681, 1.6659],
[112, 3.9258, 3.0773, 2.6857, 2.4527, 2.2954, 2.1806, 2.0924, 2.0221, 1.9645, 1.9163, 1.8751, 1.8396, 1.8085, 1.7811, 1.7566, 1.7346, 1.7147, 1.6967, 1.6802, 1.665],
[113, 3.9251, 3.0766, 2.6849, 2.452, 2.2946, 2.1798, 2.0916, 2.0213, 1.9637, 1.9155, 1.8744, 1.8388, 1.8077, 1.7803, 1.7558, 1.7338, 1.7139, 1.6958, 1.6793, 1.6642],
[114, 3.9243, 3.0758, 2.6842, 2.4513, 2.2939, 2.1791, 2.0909, 2.0206, 1.963, 1.9147, 1.8736, 1.8381, 1.8069, 1.7795, 1.755, 1.733, 1.7131, 1.695, 1.6785, 1.6633],
[115, 3.9236, 3.0751, 2.6835, 2.4506, 2.2932, 2.1784, 2.0902, 2.0199, 1.9623, 1.914, 1.8729, 1.8373, 1.8062, 1.7787, 1.7542, 1.7322, 1.7123, 1.6942, 1.6777, 1.6625],
[116, 3.9228, 3.0744, 2.6828, 2.4499, 2.2925, 2.1777, 2.0895, 2.0192, 1.9615, 1.9132, 1.8721, 1.8365, 1.8054, 1.7779, 1.7534, 1.7314, 1.7115, 1.6934, 1.6769, 1.6617],
[117, 3.9222, 3.0738, 2.6821, 2.4492, 2.2918, 2.177, 2.0888, 2.0185, 1.9608, 1.9125, 1.8714, 1.8358, 1.8047, 1.7772, 1.7527, 1.7307, 1.7108, 1.6927, 1.6761, 1.6609],
[118, 3.9215, 3.0731, 2.6815, 2.4485, 2.2912, 2.1763, 2.0881, 2.0178, 1.9601, 1.9118, 1.8707, 1.8351, 1.804, 1.7765, 1.752, 1.7299, 1.71, 1.6919, 1.6754, 1.6602],
[119, 3.9208, 3.0724, 2.6808, 2.4479, 2.2905, 2.1757, 2.0874, 2.0171, 1.9594, 1.9111, 1.87, 1.8344, 1.8032, 1.7757, 1.7512, 1.7292, 1.7093, 1.6912, 1.6746, 1.6594],
[120, 3.9202, 3.0718, 2.6802, 2.4472, 2.2899, 2.175, 2.0868, 2.0164, 1.9588, 1.9105, 1.8693, 1.8337, 1.8026, 1.775, 1.7505, 1.7285, 1.7085, 1.6904, 1.6739, 1.6587],
[121, 3.9194, 3.0712, 2.6795, 2.4466, 2.2892, 2.1744, 2.0861, 2.0158, 1.9581, 1.9098, 1.8686, 1.833, 1.8019, 1.7743, 1.7498, 1.7278, 1.7078, 1.6897, 1.6732, 1.6579],
[122, 3.9188, 3.0705, 2.6789, 2.446, 2.2886, 2.1737, 2.0855, 2.0151, 1.9575, 1.9091, 1.868, 1.8324, 1.8012, 1.7736, 1.7491, 1.727, 1.7071, 1.689, 1.6724, 1.6572],
[123, 3.9181, 3.0699, 2.6783, 2.4454, 2.288, 2.1731, 2.0849, 2.0145, 1.9568, 1.9085, 1.8673, 1.8317, 1.8005, 1.773, 1.7484, 1.7264, 1.7064, 1.6883, 1.6717, 1.6565],
[124, 3.9176, 3.0693, 2.6777, 2.4448, 2.2874, 2.1725, 2.0842, 2.0139, 1.9562, 1.9078, 1.8667, 1.831, 1.7999, 1.7723, 1.7478, 1.7257, 1.7058, 1.6876, 1.6711, 1.6558],
[125, 3.9169, 3.0687, 2.6771, 2.4442, 2.2868, 2.1719, 2.0836, 2.0133, 1.9556, 1.9072, 1.866, 1.8304, 1.7992, 1.7717, 1.7471, 1.725, 1.7051, 1.6869, 1.6704, 1.6551],
[126, 3.9163, 3.0681, 2.6765, 2.4436, 2.2862, 2.1713, 2.083, 2.0126, 1.955, 1.9066, 1.8654, 1.8298, 1.7986, 1.771, 1.7464, 1.7244, 1.7044, 1.6863, 1.6697, 1.6544],
[127, 3.9157, 3.0675, 2.6759, 2.443, 2.2856, 2.1707, 2.0824, 2.0121, 1.9544, 1.906, 1.8648, 1.8291, 1.7979, 1.7704, 1.7458, 1.7237, 1.7038, 1.6856, 1.669, 1.6538],
[128, 3.9151, 3.0669, 2.6754, 2.4424, 2.285, 2.1701, 2.0819, 2.0115, 1.9538, 1.9054, 1.8642, 1.8285, 1.7974, 1.7698, 1.7452, 1.7231, 1.7031, 1.685, 1.6684, 1.6531],
[129, 3.9145, 3.0664, 2.6749, 2.4419, 2.2845, 2.1696, 2.0813, 2.0109, 1.9532, 1.9048, 1.8636, 1.828, 1.7967, 1.7692, 1.7446, 1.7225, 1.7025, 1.6843, 1.6677, 1.6525],
[130, 3.914, 3.0659, 2.6743, 2.4414, 2.2839, 2.169, 2.0807, 2.0103, 1.9526, 1.9042, 1.863, 1.8273, 1.7962, 1.7685, 1.744, 1.7219, 1.7019, 1.6837, 1.6671, 1.6519],
[131, 3.9134, 3.0653, 2.6737, 2.4408, 2.2834, 2.1685, 2.0802, 2.0098, 1.9521, 1.9037, 1.8624, 1.8268, 1.7956, 1.768, 1.7434, 1.7213, 1.7013, 1.6831, 1.6665, 1.6513],
[132, 3.9129, 3.0648, 2.6732, 2.4403, 2.2829, 2.168, 2.0796, 2.0092, 1.9515, 1.9031, 1.8619, 1.8262, 1.795, 1.7674, 1.7428, 1.7207, 1.7007, 1.6825, 1.6659, 1.6506],
[133, 3.9123, 3.0642, 2.6727, 2.4398, 2.2823, 2.1674, 2.0791, 2.0087, 1.951, 1.9026, 1.8613, 1.8256, 1.7944, 1.7668, 1.7422, 1.7201, 1.7001, 1.6819, 1.6653, 1.65],
[134, 3.9118, 3.0637, 2.6722, 2.4392, 2.2818, 2.1669, 2.0786, 2.0082, 1.9504, 1.902, 1.8608, 1.8251, 1.7939, 1.7662, 1.7416, 1.7195, 1.6995, 1.6813, 1.6647, 1.6494],
[135, 3.9112, 3.0632, 2.6717, 2.4387, 2.2813, 2.1664, 2.0781, 2.0076, 1.9499, 1.9015, 1.8602, 1.8245, 1.7933, 1.7657, 1.7411, 1.719, 1.6989, 1.6808, 1.6641, 1.6488],
[136, 3.9108, 3.0627, 2.6712, 2.4382, 2.2808, 2.1659, 2.0775, 2.0071, 1.9494, 1.901, 1.8597, 1.824, 1.7928, 1.7651, 1.7405, 1.7184, 1.6984, 1.6802, 1.6635, 1.6483],
[137, 3.9102, 3.0622, 2.6707, 2.4378, 2.2803, 2.1654, 2.077, 2.0066, 1.9488, 1.9004, 1.8592, 1.8235, 1.7922, 1.7646, 1.74, 1.7178, 1.6978, 1.6796, 1.663, 1.6477],
[138, 3.9098, 3.0617, 2.6702, 2.4373, 2.2798, 2.1649, 2.0766, 2.0061, 1.9483, 1.8999, 1.8586, 1.823, 1.7917, 1.7641, 1.7394, 1.7173, 1.6973, 1.6791, 1.6624, 1.6471],
[139, 3.9092, 3.0613, 2.6697, 2.4368, 2.2794, 2.1644, 2.0761, 2.0056, 1.9478, 1.8994, 1.8581, 1.8224, 1.7912, 1.7635, 1.7389, 1.7168, 1.6967, 1.6785, 1.6619, 1.6466],
[140, 3.9087, 3.0608, 2.6692, 2.4363, 2.2789, 2.1639, 2.0756, 2.0051, 1.9473, 1.8989, 1.8576, 1.8219, 1.7907, 1.763, 1.7384, 1.7162, 1.6962, 1.678, 1.6613, 1.646],
[141, 3.9083, 3.0603, 2.6688, 2.4359, 2.2784, 2.1634, 2.0751, 2.0046, 1.9469, 1.8984, 1.8571, 1.8214, 1.7901, 1.7625, 1.7379, 1.7157, 1.6957, 1.6775, 1.6608, 1.6455],
[142, 3.9078, 3.0598, 2.6683, 2.4354, 2.2779, 2.163, 2.0747, 2.0042, 1.9464, 1.8979, 1.8566, 1.8209, 1.7897, 1.762, 1.7374, 1.7152, 1.6952, 1.6769, 1.6603, 1.645],
[143, 3.9073, 3.0594, 2.6679, 2.435, 2.2775, 2.1625, 2.0742, 2.0037, 1.9459, 1.8975, 1.8562, 1.8204, 1.7892, 1.7615, 1.7368, 1.7147, 1.6946, 1.6764, 1.6598, 1.6444],
[144, 3.9068, 3.0589, 2.6675, 2.4345, 2.277, 2.1621, 2.0737, 2.0033, 1.9455, 1.897, 1.8557, 1.82, 1.7887, 1.761, 1.7364, 1.7142, 1.6941, 1.6759, 1.6592, 1.6439],
[145, 3.9064, 3.0585, 2.667, 2.4341, 2.2766, 2.1617, 2.0733, 2.0028, 1.945, 1.8965, 1.8552, 1.8195, 1.7882, 1.7605, 1.7359, 1.7137, 1.6936, 1.6754, 1.6587, 1.6434],
[146, 3.906, 3.0581, 2.6666, 2.4337, 2.2762, 2.1612, 2.0728, 2.0024, 1.9445, 1.8961, 1.8548, 1.819, 1.7877, 1.7601, 1.7354, 1.7132, 1.6932, 1.6749, 1.6582, 1.6429],
[147, 3.9055, 3.0576, 2.6662, 2.4332, 2.2758, 2.1608, 2.0724, 2.0019, 1.9441, 1.8956, 1.8543, 1.8186, 1.7873, 1.7596, 1.7349, 1.7127, 1.6927, 1.6744, 1.6578, 1.6424],
[148, 3.9051, 3.0572, 2.6657, 2.4328, 2.2753, 2.1604, 2.072, 2.0015, 1.9437, 1.8952, 1.8539, 1.8181, 1.7868, 1.7591, 1.7344, 1.7123, 1.6922, 1.6739, 1.6573, 1.6419],
[149, 3.9046, 3.0568, 2.6653, 2.4324, 2.2749, 2.1599, 2.0716, 2.0011, 1.9432, 1.8947, 1.8534, 1.8177, 1.7864, 1.7587, 1.734, 1.7118, 1.6917, 1.6735, 1.6568, 1.6414],
[150, 3.9042, 3.0564, 2.6649, 2.4319, 2.2745, 2.1595, 2.0711, 2.0006, 1.9428, 1.8943, 1.853, 1.8172, 1.7859, 1.7582, 1.7335, 1.7113, 1.6913, 1.673, 1.6563, 1.641],
[151, 3.9038, 3.056, 2.6645, 2.4315, 2.2741, 2.1591, 2.0707, 2.0002, 1.9424, 1.8939, 1.8526, 1.8168, 1.7855, 1.7578, 1.7331, 1.7109, 1.6908, 1.6726, 1.6558, 1.6405],
[152, 3.9033, 3.0555, 2.6641, 2.4312, 2.2737, 2.1587, 2.0703, 1.9998, 1.942, 1.8935, 1.8521, 1.8163, 1.785, 1.7573, 1.7326, 1.7104, 1.6904, 1.6721, 1.6554, 1.64],
[153, 3.903, 3.0552, 2.6637, 2.4308, 2.2733, 2.1583, 2.0699, 1.9994, 1.9416, 1.8931, 1.8517, 1.8159, 1.7846, 1.7569, 1.7322, 1.71, 1.6899, 1.6717, 1.6549, 1.6396],
[154, 3.9026, 3.0548, 2.6634, 2.4304, 2.2729, 2.1579, 2.0695, 1.999, 1.9412, 1.8926, 1.8513, 1.8155, 1.7842, 1.7565, 1.7318, 1.7096, 1.6895, 1.6712, 1.6545, 1.6391],
[155, 3.9021, 3.0544, 2.6629, 2.43, 2.2725, 2.1575, 2.0691, 1.9986, 1.9407, 1.8923, 1.8509, 1.8151, 1.7838, 1.7561, 1.7314, 1.7091, 1.6891, 1.6708, 1.654, 1.6387],
[156, 3.9018, 3.054, 2.6626, 2.4296, 2.2722, 2.1571, 2.0687, 1.9982, 1.9403, 1.8918, 1.8505, 1.8147, 1.7834, 1.7557, 1.7309, 1.7087, 1.6886, 1.6703, 1.6536, 1.6383],
[157, 3.9014, 3.0537, 2.6622, 2.4293, 2.2717, 2.1568, 2.0684, 1.9978, 1.94, 1.8915, 1.8501, 1.8143, 1.7829, 1.7552, 1.7305, 1.7083, 1.6882, 1.6699, 1.6532, 1.6378],
[158, 3.901, 3.0533, 2.6618, 2.4289, 2.2714, 2.1564, 2.068, 1.9974, 1.9396, 1.8911, 1.8497, 1.8139, 1.7826, 1.7548, 1.7301, 1.7079, 1.6878, 1.6695, 1.6528, 1.6374],
[159, 3.9006, 3.0529, 2.6615, 2.4285, 2.271, 2.156, 2.0676, 1.997, 1.9392, 1.8907, 1.8493, 1.8135, 1.7822, 1.7544, 1.7297, 1.7075, 1.6874, 1.6691, 1.6524, 1.637],
[160, 3.9002, 3.0525, 2.6611, 2.4282, 2.2706, 2.1556, 2.0672, 1.9967, 1.9388, 1.8903, 1.8489, 1.8131, 1.7818, 1.754, 1.7293, 1.7071, 1.687, 1.6687, 1.6519, 1.6366],
[161, 3.8998, 3.0522, 2.6607, 2.4278, 2.2703, 2.1553, 2.0669, 1.9963, 1.9385, 1.8899, 1.8485, 1.8127, 1.7814, 1.7537, 1.7289, 1.7067, 1.6866, 1.6683, 1.6515, 1.6361],
[162, 3.8995, 3.0518, 2.6604, 2.4275, 2.27, 2.155, 2.0665, 1.9959, 1.9381, 1.8895, 1.8482, 1.8124, 1.781, 1.7533, 1.7285, 1.7063, 1.6862, 1.6679, 1.6511, 1.6357],
[163, 3.8991, 3.0515, 2.6601, 2.4271, 2.2696, 2.1546, 2.0662, 1.9956, 1.9377, 1.8892, 1.8478, 1.812, 1.7806, 1.7529, 1.7282, 1.7059, 1.6858, 1.6675, 1.6507, 1.6353],
[164, 3.8987, 3.0512, 2.6597, 2.4268, 2.2693, 2.1542, 2.0658, 1.9953, 1.9374, 1.8888, 1.8474, 1.8116, 1.7803, 1.7525, 1.7278, 1.7055, 1.6854, 1.6671, 1.6503, 1.6349],
[165, 3.8985, 3.0508, 2.6594, 2.4264, 2.2689, 2.1539, 2.0655, 1.9949, 1.937, 1.8885, 1.8471, 1.8112, 1.7799, 1.7522, 1.7274, 1.7052, 1.685, 1.6667, 1.6499, 1.6345],
[166, 3.8981, 3.0505, 2.6591, 2.4261, 2.2686, 2.1536, 2.0651, 1.9945, 1.9367, 1.8881, 1.8467, 1.8109, 1.7795, 1.7518, 1.727, 1.7048, 1.6846, 1.6663, 1.6496, 1.6341],
[167, 3.8977, 3.0502, 2.6587, 2.4258, 2.2683, 2.1533, 2.0648, 1.9942, 1.9363, 1.8878, 1.8464, 1.8105, 1.7792, 1.7514, 1.7266, 1.7044, 1.6843, 1.6659, 1.6492, 1.6338],
[168, 3.8974, 3.0498, 2.6584, 2.4254, 2.268, 2.1529, 2.0645, 1.9939, 1.936, 1.8874, 1.846, 1.8102, 1.7788, 1.7511, 1.7263, 1.704, 1.6839, 1.6656, 1.6488, 1.6334],
[169, 3.8971, 3.0495, 2.6581, 2.4251, 2.2676, 2.1526, 2.0641, 1.9936, 1.9357, 1.8871, 1.8457, 1.8099, 1.7785, 1.7507, 1.7259, 1.7037, 1.6835, 1.6652, 1.6484, 1.633],
[170, 3.8967, 3.0492, 2.6578, 2.4248, 2.2673, 2.1523, 2.0638, 1.9932, 1.9353, 1.8868, 1.8454, 1.8095, 1.7781, 1.7504, 1.7256, 1.7033, 1.6832, 1.6648, 1.6481, 1.6326],
[171, 3.8965, 3.0488, 2.6575, 2.4245, 2.267, 2.152, 2.0635, 1.9929, 1.935, 1.8864, 1.845, 1.8092, 1.7778, 1.75, 1.7252, 1.703, 1.6828, 1.6645, 1.6477, 1.6323],
[172, 3.8961, 3.0485, 2.6571, 2.4242, 2.2667, 2.1516, 2.0632, 1.9926, 1.9347, 1.8861, 1.8447, 1.8088, 1.7774, 1.7497, 1.7249, 1.7026, 1.6825, 1.6641, 1.6473, 1.6319],
[173, 3.8958, 3.0482, 2.6568, 2.4239, 2.2664, 2.1513, 2.0628, 1.9923, 1.9343, 1.8858, 1.8443, 1.8085, 1.7771, 1.7493, 1.7246, 1.7023, 1.6821, 1.6638, 1.647, 1.6316],
[174, 3.8954, 3.0479, 2.6566, 2.4236, 2.266, 2.151, 2.0626, 1.9919, 1.934, 1.8855, 1.844, 1.8082, 1.7768, 1.749, 1.7242, 1.7019, 1.6818, 1.6634, 1.6466, 1.6312],
[175, 3.8952, 3.0476, 2.6563, 2.4233, 2.2658, 2.1507, 2.0622, 1.9916, 1.9337, 1.8852, 1.8437, 1.8078, 1.7764, 1.7487, 1.7239, 1.7016, 1.6814, 1.6631, 1.6463, 1.6309],
[176, 3.8948, 3.0473, 2.6559, 2.423, 2.2655, 2.1504, 2.0619, 1.9913, 1.9334, 1.8848, 1.8434, 1.8075, 1.7761, 1.7483, 1.7236, 1.7013, 1.6811, 1.6628, 1.646, 1.6305],
[177, 3.8945, 3.047, 2.6556, 2.4227, 2.2652, 2.1501, 2.0616, 1.991, 1.9331, 1.8845, 1.8431, 1.8072, 1.7758, 1.748, 1.7232, 1.7009, 1.6808, 1.6624, 1.6456, 1.6302],
[178, 3.8943, 3.0467, 2.6554, 2.4224, 2.2649, 2.1498, 2.0613, 1.9907, 1.9328, 1.8842, 1.8428, 1.8069, 1.7755, 1.7477, 1.7229, 1.7006, 1.6805, 1.6621, 1.6453, 1.6298],
[179, 3.8939, 3.0465, 2.6551, 2.4221, 2.2646, 2.1495, 2.0611, 1.9904, 1.9325, 1.8839, 1.8425, 1.8066, 1.7752, 1.7474, 1.7226, 1.7003, 1.6801, 1.6618, 1.645, 1.6295],
[180, 3.8936, 3.0462, 2.6548, 2.4218, 2.2643, 2.1492, 2.0608, 1.9901, 1.9322, 1.8836, 1.8422, 1.8063, 1.7749, 1.7471, 1.7223, 1.7, 1.6798, 1.6614, 1.6446, 1.6292],
[181, 3.8933, 3.0458, 2.6545, 2.4216, 2.264, 2.149, 2.0605, 1.9899, 1.9319, 1.8833, 1.8419, 1.806, 1.7746, 1.7468, 1.7219, 1.6997, 1.6795, 1.6611, 1.6443, 1.6289],
[182, 3.8931, 3.0456, 2.6543, 2.4213, 2.2638, 2.1487, 2.0602, 1.9896, 1.9316, 1.883, 1.8416, 1.8057, 1.7743, 1.7465, 1.7217, 1.6994, 1.6792, 1.6608, 1.644, 1.6286],
[183, 3.8928, 3.0453, 2.654, 2.421, 2.2635, 2.1484, 2.0599, 1.9893, 1.9313, 1.8827, 1.8413, 1.8054, 1.774, 1.7462, 1.7214, 1.6991, 1.6789, 1.6605, 1.6437, 1.6282],
[184, 3.8925, 3.045, 2.6537, 2.4207, 2.2632, 2.1481, 2.0596, 1.989, 1.9311, 1.8825, 1.841, 1.8051, 1.7737, 1.7459, 1.721, 1.6987, 1.6786, 1.6602, 1.6434, 1.6279],
[185, 3.8923, 3.0448, 2.6534, 2.4205, 2.263, 2.1479, 2.0594, 1.9887, 1.9308, 1.8822, 1.8407, 1.8048, 1.7734, 1.7456, 1.7208, 1.6984, 1.6783, 1.6599, 1.643, 1.6276],
[186, 3.892, 3.0445, 2.6531, 2.4202, 2.2627, 2.1476, 2.0591, 1.9885, 1.9305, 1.8819, 1.8404, 1.8045, 1.7731, 1.7453, 1.7205, 1.6981, 1.678, 1.6596, 1.6428, 1.6273],
[187, 3.8917, 3.0442, 2.6529, 2.4199, 2.2624, 2.1473, 2.0588, 1.9882, 1.9302, 1.8816, 1.8401, 1.8042, 1.7728, 1.745, 1.7202, 1.6979, 1.6777, 1.6593, 1.6424, 1.627],
[188, 3.8914, 3.044, 2.6526, 2.4197, 2.2621, 2.1471, 2.0586, 1.9879, 1.9299, 1.8814, 1.8399, 1.804, 1.7725, 1.7447, 1.7199, 1.6976, 1.6774, 1.659, 1.6421, 1.6267],
[189, 3.8912, 3.0437, 2.6524, 2.4195, 2.2619, 2.1468, 2.0583, 1.9877, 1.9297, 1.8811, 1.8396, 1.8037, 1.7722, 1.7444, 1.7196, 1.6973, 1.6771, 1.6587, 1.6418, 1.6264],
[190, 3.8909, 3.0435, 2.6521, 2.4192, 2.2617, 2.1466, 2.0581, 1.9874, 1.9294, 1.8808, 1.8393, 1.8034, 1.772, 1.7441, 1.7193, 1.697, 1.6768, 1.6584, 1.6416, 1.6261],
[191, 3.8906, 3.0432, 2.6519, 2.4189, 2.2614, 2.1463, 2.0578, 1.9871, 1.9292, 1.8805, 1.8391, 1.8032, 1.7717, 1.7439, 1.719, 1.6967, 1.6765, 1.6581, 1.6413, 1.6258],
[192, 3.8903, 3.043, 2.6516, 2.4187, 2.2611, 2.1461, 2.0575, 1.9869, 1.9289, 1.8803, 1.8388, 1.8029, 1.7714, 1.7436, 1.7188, 1.6964, 1.6762, 1.6578, 1.641, 1.6255],
[193, 3.8901, 3.0427, 2.6514, 2.4184, 2.2609, 2.1458, 2.0573, 1.9866, 1.9286, 1.88, 1.8385, 1.8026, 1.7712, 1.7433, 1.7185, 1.6961, 1.6759, 1.6575, 1.6407, 1.6252],
[194, 3.8899, 3.0425, 2.6512, 2.4182, 2.2606, 2.1456, 2.057, 1.9864, 1.9284, 1.8798, 1.8383, 1.8023, 1.7709, 1.7431, 1.7182, 1.6959, 1.6757, 1.6572, 1.6404, 1.6249],
[195, 3.8896, 3.0422, 2.6509, 2.418, 2.2604, 2.1453, 2.0568, 1.9861, 1.9281, 1.8795, 1.838, 1.8021, 1.7706, 1.7428, 1.7179, 1.6956, 1.6754, 1.657, 1.6401, 1.6247],
[196, 3.8893, 3.042, 2.6507, 2.4177, 2.2602, 2.1451, 2.0566, 1.9859, 1.9279, 1.8793, 1.8377, 1.8018, 1.7704, 1.7425, 1.7177, 1.6953, 1.6751, 1.6567, 1.6399, 1.6244],
[197, 3.8891, 3.0418, 2.6504, 2.4175, 2.26, 2.1448, 2.0563, 1.9856, 1.9277, 1.879, 1.8375, 1.8016, 1.7701, 1.7423, 1.7174, 1.6951, 1.6748, 1.6564, 1.6396, 1.6241],
[198, 3.8889, 3.0415, 2.6502, 2.4173, 2.2597, 2.1446, 2.0561, 1.9854, 1.9274, 1.8788, 1.8373, 1.8013, 1.7699, 1.742, 1.7172, 1.6948, 1.6746, 1.6562, 1.6393, 1.6238],
[199, 3.8886, 3.0413, 2.65, 2.417, 2.2595, 2.1444, 2.0558, 1.9852, 1.9272, 1.8785, 1.837, 1.8011, 1.7696, 1.7418, 1.7169, 1.6946, 1.6743, 1.6559, 1.6391, 1.6236],
[200, 3.8883, 3.041, 2.6497, 2.4168, 2.2592, 2.1441, 2.0556, 1.9849, 1.9269, 1.8783, 1.8368, 1.8008, 1.7694, 1.7415, 1.7166, 1.6943, 1.6741, 1.6557, 1.6388, 1.62]])
    return ftest[row][col]

def tcalc(nf,p):
    """
     t-table for nf degrees of freedom (95% confidence)
    """
#
    if p==.05:
        if nf> 2: t= 4.3027
        if nf> 3: t= 3.1824
        if nf> 4: t= 2.7765
        if nf> 5: t= 2.5706
        if nf> 6: t= 2.4469
        if nf> 7: t= 2.3646
        if nf> 8: t= 2.3060
        if nf> 9: t= 2.2622
        if nf> 10: t= 2.2281
        if nf> 11: t= 2.2010
        if nf> 12: t= 2.1788
        if nf> 13: t= 2.1604
        if nf> 14: t= 2.1448
        if nf> 15: t= 2.1315
        if nf> 16: t= 2.1199
        if nf> 17: t= 2.1098
        if nf> 18: t= 2.1009
        if nf> 19: t= 2.0930
        if nf> 20: t= 2.0860
        if nf> 21: t= 2.0796
        if nf> 22: t= 2.0739
        if nf> 23: t= 2.0687
        if nf> 24: t= 2.0639
        if nf> 25: t= 2.0595
        if nf> 26: t= 2.0555
        if nf> 27: t= 2.0518
        if nf> 28: t= 2.0484
        if nf> 29: t= 2.0452
        if nf> 30: t= 2.0423
        if nf> 31: t= 2.0395
        if nf> 32: t= 2.0369
        if nf> 33: t= 2.0345
        if nf> 34: t= 2.0322
        if nf> 35: t= 2.0301
        if nf> 36: t= 2.0281
        if nf> 37: t= 2.0262
        if nf> 38: t= 2.0244
        if nf> 39: t= 2.0227
        if nf> 40: t= 2.0211
        if nf> 41: t= 2.0195
        if nf> 42: t= 2.0181
        if nf> 43: t= 2.0167
        if nf> 44: t= 2.0154
        if nf> 45: t= 2.0141
        if nf> 46: t= 2.0129
        if nf> 47: t= 2.0117
        if nf> 48: t= 2.0106
        if nf> 49: t= 2.0096
        if nf> 50: t= 2.0086
        if nf> 51: t= 2.0076
        if nf> 52: t= 2.0066
        if nf> 53: t= 2.0057
        if nf> 54: t= 2.0049
        if nf> 55: t= 2.0040
        if nf> 56: t= 2.0032
        if nf> 57: t= 2.0025
        if nf> 58: t= 2.0017
        if nf> 59: t= 2.0010
        if nf> 60: t= 2.0003
        if nf> 61: t= 1.9996
        if nf> 62: t= 1.9990
        if nf> 63: t= 1.9983
        if nf> 64: t= 1.9977
        if nf> 65: t= 1.9971
        if nf> 66: t= 1.9966
        if nf> 67: t= 1.9960
        if nf> 68: t= 1.9955
        if nf> 69: t= 1.9949
        if nf> 70: t= 1.9944
        if nf> 71: t= 1.9939
        if nf> 72: t= 1.9935
        if nf> 73: t= 1.9930
        if nf> 74: t= 1.9925
        if nf> 75: t= 1.9921
        if nf> 76: t= 1.9917
        if nf> 77: t= 1.9913
        if nf> 78: t= 1.9908
        if nf> 79: t= 1.9905
        if nf> 80: t= 1.9901
        if nf> 81: t= 1.9897
        if nf> 82: t= 1.9893
        if nf> 83: t= 1.9890
        if nf> 84: t= 1.9886
        if nf> 85: t= 1.9883
        if nf> 86: t= 1.9879
        if nf> 87: t= 1.9876
        if nf> 88: t= 1.9873
        if nf> 89: t= 1.9870
        if nf> 90: t= 1.9867
        if nf> 91: t= 1.9864
        if nf> 92: t= 1.9861
        if nf> 93: t= 1.9858
        if nf> 94: t= 1.9855
        if nf> 95: t= 1.9852
        if nf> 96: t= 1.9850
        if nf> 97: t= 1.9847
        if nf> 98: t= 1.9845
        if nf> 99: t= 1.9842
        if nf> 100: t= 1.9840
        return t
#
    elif p==.01:
        if nf> 2: t= 9.9250
        if nf> 3: t= 5.8408
        if nf> 4: t= 4.6041
        if nf> 5: t= 4.0321
        if nf> 6: t= 3.7074
        if nf> 7: t= 3.4995
        if nf> 8: t= 3.3554
        if nf> 9: t= 3.2498
        if nf> 10: t= 3.1693
        if nf> 11: t= 3.1058
        if nf> 12: t= 3.0545
        if nf> 13: t= 3.0123
        if nf> 14: t= 2.9768
        if nf> 15: t= 2.9467
        if nf> 16: t= 2.9208
        if nf> 17: t= 2.8982
        if nf> 18: t= 2.8784
        if nf> 19: t= 2.8609
        if nf> 20: t= 2.8453
        if nf> 21: t= 2.8314
        if nf> 22: t= 2.8188
        if nf> 23: t= 2.8073
        if nf> 24: t= 2.7970
        if nf> 25: t= 2.7874
        if nf> 26: t= 2.7787
        if nf> 27: t= 2.7707
        if nf> 28: t= 2.7633
        if nf> 29: t= 2.7564
        if nf> 30: t= 2.7500
        if nf> 31: t= 2.7440
        if nf> 32: t= 2.7385
        if nf> 33: t= 2.7333
        if nf> 34: t= 2.7284
        if nf> 35: t= 2.7238
        if nf> 36: t= 2.7195
        if nf> 37: t= 2.7154
        if nf> 38: t= 2.7116
        if nf> 39: t= 2.7079
        if nf> 40: t= 2.7045
        if nf> 41: t= 2.7012
        if nf> 42: t= 2.6981
        if nf> 43: t= 2.6951
        if nf> 44: t= 2.6923
        if nf> 45: t= 2.6896
        if nf> 46: t= 2.6870
        if nf> 47: t= 2.6846
        if nf> 48: t= 2.6822
        if nf> 49: t= 2.6800
        if nf> 50: t= 2.6778
        if nf> 51: t= 2.6757
        if nf> 52: t= 2.6737
        if nf> 53: t= 2.6718
        if nf> 54: t= 2.6700
        if nf> 55: t= 2.6682
        if nf> 56: t= 2.6665
        if nf> 57: t= 2.6649
        if nf> 58: t= 2.6633
        if nf> 59: t= 2.6618
        if nf> 60: t= 2.6603
        if nf> 61: t= 2.6589
        if nf> 62: t= 2.6575
        if nf> 63: t= 2.6561
        if nf> 64: t= 2.6549
        if nf> 65: t= 2.6536
        if nf> 66: t= 2.6524
        if nf> 67: t= 2.6512
        if nf> 68: t= 2.6501
        if nf> 69: t= 2.6490
        if nf> 70: t= 2.6479
        if nf> 71: t= 2.6469
        if nf> 72: t= 2.6458
        if nf> 73: t= 2.6449
        if nf> 74: t= 2.6439
        if nf> 75: t= 2.6430
        if nf> 76: t= 2.6421
        if nf> 77: t= 2.6412
        if nf> 78: t= 2.6403
        if nf> 79: t= 2.6395
        if nf> 80: t= 2.6387
        if nf> 81: t= 2.6379
        if nf> 82: t= 2.6371
        if nf> 83: t= 2.6364
        if nf> 84: t= 2.6356
        if nf> 85: t= 2.6349
        if nf> 86: t= 2.6342
        if nf> 87: t= 2.6335
        if nf> 88: t= 2.6329
        if nf> 89: t= 2.6322
        if nf> 90: t= 2.6316
        if nf> 91: t= 2.6309
        if nf> 92: t= 2.6303
        if nf> 93: t= 2.6297
        if nf> 94: t= 2.6291
        if nf> 95: t= 2.6286
        if nf> 96: t= 2.6280
        if nf> 97: t= 2.6275
        if nf> 98: t= 2.6269
        if nf> 99: t= 2.6264
        if nf> 100: t= 2.6259
        return t
        return t
    else:
        return 0
#
def sbar(Ss):
    """
    calculate average s,sigma from list of "s"s.
    """
    npts=len(Ss)
    Ss=numpy.array(Ss).transpose()
    avd,avs=[],[]
    #D=numpy.array([Ss[0],Ss[1],Ss[2],Ss[3]+0.5*(Ss[0]+Ss[1]),Ss[4]+0.5*(Ss[1]+Ss[2]),Ss[5]+0.5*(Ss[0]+Ss[2])]).transpose()
    D=numpy.array([Ss[0],Ss[1],Ss[2],Ss[3]+0.5*(Ss[0]+Ss[1]),Ss[4]+0.5*(Ss[1]+Ss[2]),Ss[5]+0.5*(Ss[0]+Ss[2])])
    for j in range(6):
        avd.append(numpy.average(D[j]))
        avs.append(numpy.average(Ss[j]))
    D=D.transpose()
    #for s in Ss:
    #    print 'from sbar: ',s
    #    D.append(s[:]) # append a copy of s
    #    D[-1][3]=D[-1][3]+0.5*(s[0]+s[1])
    #    D[-1][4]=D[-1][4]+0.5*(s[1]+s[2])
    #    D[-1][5]=D[-1][5]+0.5*(s[0]+s[2])
    #    for j in range(6):
    #        avd[j]+=(D[-1][j])/float(npts)
    #        avs[j]+=(s[j])/float(npts)
#   calculate sigma
    nf=(npts-1)*6 # number of degrees of freedom
    s0=0
    Dels=(D-avd)**2
    s0=numpy.sum(Dels)
    sigma=numpy.sqrt(s0/float(nf))
    return nf,sigma,avs

def dohext(nf,sigma,s):
    """
    calculates hext parameters for nf, sigma and s
    """
#
    hpars={}
    hpars['F_crit']='0'
    hpars['F12_crit']='0'
    hpars["F"]=0
    hpars["F12"]=0
    hpars["F23"]=0
    hpars["v1_dec"]=-1
    hpars["v1_inc"]=-1
    hpars["v2_dec"]=-1
    hpars["v2_inc"]=-1
    hpars["v3_dec"]=-1
    hpars["v3_inc"]=-1
    hpars["t1"]=-1
    hpars["t2"]=-1
    hpars["t3"]=-1
    hpars["e12"]=-1
    hpars["e23"]=-1
    hpars["e13"]=-1
    if nf<0 or sigma==0:return hpars
    f=numpy.sqrt(2.*fcalc(2,nf))
    t2sum=0
    tau,Vdir=doseigs(s)
    for i in range(3): t2sum+=tau[i]**2
    chibar=(s[0]+s[1]+s[2])/3.
    hpars['F_crit']='%s'%(fcalc(5,nf))
    hpars['F12_crit']='%s'%(fcalc(2,nf))
    hpars["F"]=0.4*(t2sum-3*chibar**2)/(sigma**2)
    hpars["F12"]=0.5*((tau[0]-tau[1])/sigma)**2
    hpars["F23"]=0.5*((tau[1]-tau[2])/sigma)**2
    hpars["v1_dec"]=Vdir[0][0]
    hpars["v1_inc"]=Vdir[0][1]
    hpars["v2_dec"]=Vdir[1][0]
    hpars["v2_inc"]=Vdir[1][1]
    hpars["v3_dec"]=Vdir[2][0]
    hpars["v3_inc"]=Vdir[2][1]
    hpars["t1"]=tau[0]
    hpars["t2"]=tau[1]
    hpars["t3"]=tau[2]
    hpars["e12"]=numpy.arctan((f*sigma)/(2*abs(tau[0]-tau[1])))*180./numpy.pi
    hpars["e23"]=numpy.arctan((f*sigma)/(2*abs(tau[1]-tau[2])))*180./numpy.pi
    hpars["e13"]=numpy.arctan((f*sigma)/(2*abs(tau[0]-tau[2])))*180./numpy.pi
    return hpars
#
#
def design(npos):
    """
     make a design matrix for an anisotropy experiment
    """
    if npos==15:
#
# rotatable design of Jelinek for kappabridge (see Tauxe, 1998)
#
        A=numpy.array([[.5,.5,0,-1.,0,0],[.5,.5,0,1.,0,0],[1,.0,0,0,0,0],[.5,.5,0,-1.,0,0],[.5,.5,0,1.,0,0],[0,.5,.5,0,-1.,0],[0,.5,.5,0,1.,0],[0,1.,0,0,0,0],[0,.5,.5,0,-1.,0],[0,.5,.5,0,1.,0],[.5,0,.5,0,0,-1.],[.5,0,.5,0,0,1.],[0,0,1.,0,0,0],[.5,0,.5,0,0,-1.],[.5,0,.5,0,0,1.]]) #  design matrix for 15 measurment positions
    elif npos==6:
        A=numpy.array([[1.,0,0,0,0,0],[0,1.,0,0,0,0],[0,0,1.,0,0,0],[.5,.5,0,1.,0,0],[0,.5,.5,0,1.,0],[.5,0,.5,0,0,1.]]) #  design matrix for 6 measurment positions

    else:
        print "measurement protocol not supported yet "
        sys.exit()
    B=numpy.dot(numpy.transpose(A),A)
    B=numpy.linalg.inv(B)
    B=numpy.dot(B,numpy.transpose(A))
    return A,B
#
#
def dok15_s(k15):
    """
    calculates least-squares matrix for 15 measurements from Jelinek [1976]
    """
#
    A,B=design(15) #  get design matrix for 15 measurements
    sbar=numpy.dot(B,k15) # get mean s
    t=(sbar[0]+sbar[1]+sbar[2]) # trace
    bulk=t/3. # bulk susceptibility
    Kbar=numpy.dot(A,sbar)  # get best fit values for K
    dels=k15-Kbar  # get deltas
    dels,sbar=dels/t,sbar/t# normalize by trace
    So= sum(dels**2)
    sigma=numpy.sqrt(So/9.) # standard deviation
    return sbar,sigma,bulk
#
def cross(v, w):
    """
     cross product of two vectors
    """
    x = v[1]*w[2] - v[2]*w[1]
    y = v[2]*w[0] - v[0]*w[2]
    z = v[0]*w[1] - v[1]*w[0]
    return [x, y, z]
#
def dosgeo(s,az,pl):
    """
     rotates  matrix a to az,pl returns  s
    """
#
    a=s2a(s) # convert to 3,3 matrix
#  first get three orthogonal axes
    X1=dir2cart((az,pl,1.))
    X2=dir2cart((az+90,0.,1.))
    X3=cross(X1,X2)
    A=numpy.transpose([X1,X2,X3])
    b=numpy.zeros((3,3,),'f') # initiale the b matrix
    for i in range(3):
        for j in range(3):
            dum=0
            for k in range(3):
                for l in range(3):
                    dum+=A[i][k]*A[j][l]*a[k][l]
            b[i][j]=dum
    return a2s(b)
#
#
def dostilt(s,bed_az,bed_dip):
    """
     rotate "s" data to stratigraphic coordinates
    """
    tau,Vdirs=doseigs(s)
    Vrot=[]
    for evec in Vdirs:
        d,i=dotilt(evec[0],evec[1],bed_az,bed_dip)
        Vrot.append([d,i])
    return doeigs_s(tau,Vrot)
#
#
def apseudo(Ss,ipar,sigma):
    """
     draw a bootstrap sample of Ss
    """
#
    Is=random.randint(0,len(Ss)-1,size=len(Ss)) # draw N random integers
    Ss=numpy.array(Ss)
    if ipar==0:
        BSs=Ss[Is]
    else: # need to recreate measurement - then do the parametric stuffr
        A,B=design(6) # get the design matrix for 6 measurements
        K,BSs=[],[]
        for k in range(len(Ss)):
            K.append(numpy.dot(A,Ss[k]))
        Pars=numpy.random.normal(K,sigma)
        for k in range(len(Ss)):
            BSs.append(numpy.dot(B,Pars[k]))
    return numpy.array(BSs)
#
def sbootpars(Taus,Vs):
    """
     get bootstrap parameters for s data
    """
#
    Tau1s,Tau2s,Tau3s=[],[],[]
    V1s,V2s,V3s=[],[],[]
    nb=len(Taus)
    bpars={}
    for k in range(nb):
        Tau1s.append(Taus[k][0])
        Tau2s.append(Taus[k][1])
        Tau3s.append(Taus[k][2])
        V1s.append(Vs[k][0])
        V2s.append(Vs[k][1])
        V3s.append(Vs[k][2])
    x,sig=gausspars(Tau1s)
    bpars["t1_sigma"]=sig
    x,sig=gausspars(Tau2s)
    bpars["t2_sigma"]=sig
    x,sig=gausspars(Tau3s)
    bpars["t3_sigma"]=sig
    kpars=dokent(V1s,len(V1s))
    bpars["v1_dec"]=kpars["dec"]
    bpars["v1_inc"]=kpars["inc"]
    bpars["v1_zeta"]=kpars["Zeta"]*numpy.sqrt(nb)
    bpars["v1_eta"]=kpars["Eta"]*numpy.sqrt(nb)
    bpars["v1_zeta_dec"]=kpars["Zdec"]
    bpars["v1_zeta_inc"]=kpars["Zinc"]
    bpars["v1_eta_dec"]=kpars["Edec"]
    bpars["v1_eta_inc"]=kpars["Einc"]
    kpars=dokent(V2s,len(V2s))
    bpars["v2_dec"]=kpars["dec"]
    bpars["v2_inc"]=kpars["inc"]
    bpars["v2_zeta"]=kpars["Zeta"]*numpy.sqrt(nb)
    bpars["v2_eta"]=kpars["Eta"]*numpy.sqrt(nb)
    bpars["v2_zeta_dec"]=kpars["Zdec"]
    bpars["v2_zeta_inc"]=kpars["Zinc"]
    bpars["v2_eta_dec"]=kpars["Edec"]
    bpars["v2_eta_inc"]=kpars["Einc"]
    kpars=dokent(V3s,len(V3s))
    bpars["v3_dec"]=kpars["dec"]
    bpars["v3_inc"]=kpars["inc"]
    bpars["v3_zeta"]=kpars["Zeta"]*numpy.sqrt(nb)
    bpars["v3_eta"]=kpars["Eta"]*numpy.sqrt(nb)
    bpars["v3_zeta_dec"]=kpars["Zdec"]
    bpars["v3_zeta_inc"]=kpars["Zinc"]
    bpars["v3_eta_dec"]=kpars["Edec"]
    bpars["v3_eta_inc"]=kpars["Einc"]
    return bpars
#
#
def s_boot(Ss,ipar,nb):
    """
     returns bootstrap parameters for S data
    """
    npts=len(Ss)
# get average s for whole dataset
    nf,Sigma,avs=sbar(Ss)
    Tmean,Vmean=doseigs(avs) # get eigenvectors of mean tensor
#
# now do bootstrap to collect Vs and taus of bootstrap means
#
    Taus,Vs=[],[]  # number of bootstraps, list of bootstrap taus and eigenvectors
#

    for k in range(nb): # repeat nb times
#        if k%50==0:print k,' out of ',nb
        BSs=apseudo(Ss,ipar,Sigma) # get a pseudosample - if ipar=1, do a parametric bootstrap
        nf,sigma,avbs=sbar(BSs) # get bootstrap mean s
        tau,Vdirs=doseigs(avbs) # get bootstrap eigenparameters
        Taus.append(tau)
        Vs.append(Vdirs)
    return Tmean,Vmean,Taus,Vs

#
def designAARM(npos):
#
    """
    calculates B matrix for AARM calculations.
    """
    if npos!=9:
        print 'Sorry - only 9 positions available'
        sys.exit()
    Dec=[315.,225.,180.,135.,45.,90.,270.,270.,270.,90.,180.,180.,0.,0.,0.]
    Dip=[0.,0.,0.,0.,0.,-45.,-45.,0.,45.,45.,45.,-45.,-90.,-45.,45.]
    index9=[0,1, 2,5,6,7,10,11,12]
    H=[]
    for ind in range(15):
        Dir=[Dec[ind],Dip[ind],1.]
        H.append(dir2cart(Dir))  # 15 field directionss
#
# make design matrix A
#
    A=numpy.zeros((npos*3,6),'f')
    tmpH=numpy.zeros((npos,3),'f') # define tmpH
    if npos == 9:
        for i in range(9):
            k=index9[i]
            ind=i*3
            A[ind][0]=H[k][0]
            A[ind][3]=H[k][1]
            A[ind][5]=H[k][2]
            ind=i*3+1
            A[ind][3]=H[k][0]
            A[ind][1]=H[k][1]
            A[ind][4]=H[k][2]
            ind=i*3+2
            A[ind][5]=H[k][0]
            A[ind][4]=H[k][1]
            A[ind][2]=H[k][2]
            for j in range(3):
                tmpH[i][j]=H[k][j]
        At=numpy.transpose(A)
        ATA=numpy.dot(At,A)
        ATAI=numpy.linalg.inv(ATA)
        B=numpy.dot(ATAI,At)
    else:
        print "B matrix not yet supported"
        sys.exit()
    return B,H,tmpH
#
def designATRM(npos):
#
    """
    calculates B matrix for ATRM calculations.
    """
    #if npos!=6:
    #    print 'Sorry - only 6 positions available'
    #    sys.exit()
    Dec=[0,0,  0,90,180,270,0] # for shuhui only
    Dip=[90,-90,0,0,0,0,90]
    Dec=[0,90,0,180,270,0,0,90,0]
    Dip=[0,0,90,0,0,-90,0,0,90]
    H=[]
    for ind in range(6):
        Dir=[Dec[ind],Dip[ind],1.]
        H.append(dir2cart(Dir))  # 6 field directionss
#
# make design matrix A
#
    A=numpy.zeros((npos*3,6),'f')
    tmpH=numpy.zeros((npos,3),'f') # define tmpH
    #if npos == 6:
    #    for i in range(6):
    for i in range(6):
            ind=i*3
            A[ind][0]=H[i][0]
            A[ind][3]=H[i][1]
            A[ind][5]=H[i][2]
            ind=i*3+1
            A[ind][3]=H[i][0]
            A[ind][1]=H[i][1]
            A[ind][4]=H[i][2]
            ind=i*3+2
            A[ind][5]=H[i][0]
            A[ind][4]=H[i][1]
            A[ind][2]=H[i][2]
            for j in range(3):
                tmpH[i][j]=H[i][j]
    At=numpy.transpose(A)
    ATA=numpy.dot(At,A)
    ATAI=numpy.linalg.inv(ATA)
    B=numpy.dot(ATAI,At)
    #else:
    #    print "B matrix not yet supported"
    #    sys.exit()
    return B,H,tmpH

#
def domagicmag(file,Recs):
    """
    converts a magic record back into the SIO mag format
    """
    for rec in Recs:
        type=".0"
        meths=[]
        tmp=rec["magic_method_codes"].split(':')
        for meth in tmp:
            meths.append(meth.strip())
        if 'LT-T-I' in meths: type=".1"
        if 'LT-PTRM-I' in meths: type=".2"
        if 'LT-PTRM-MD' in meths: type=".3"
        treatment=float(rec["treatment_temp"])-273
        tr='%i'%(treatment)+type
        inten='%8.7e '%(float(rec["measurement_magn_moment"])*1e3)
        outstring=rec["er_specimen_name"]+" "+tr+" "+rec["measurement_csd"]+" "+inten+" "+rec["measurement_dec"]+" "+rec["measurement_inc"]+"\n"
        file.write(outstring)
#
#
def cleanup(first_I,first_Z):
    """
     cleans up unbalanced steps
     failure can be from unbalanced final step, or from missing steps,
     this takes care of  missing steps
    """
    cont=0
    Nmin=len(first_I)
    if len(first_Z)<Nmin:Nmin=len(first_Z)
    for kk in range(Nmin):
        if first_I[kk][0]!=first_Z[kk][0]:
            print "\n WARNING: "
            if first_I[kk]<first_Z[kk]:
                del first_I[kk]
            else:
                del first_Z[kk]
            print "Unmatched step number: ",kk+1,'  ignored'
            cont=1
        if cont==1: return first_I,first_Z,cont
    return first_I,first_Z,cont
#
#
def sortarai(datablock,s,Zdiff):
    """
     sorts data block in to first_Z, first_I, etc.
    """
    first_Z,first_I,zptrm_check,ptrm_check,ptrm_tail=[],[],[],[],[]
    field,phi,theta="","",""
    starthere=0
    Treat_I,Treat_Z,Treat_PZ,Treat_PI,Treat_M=[],[],[],[],[]
    ISteps,ZSteps,PISteps,PZSteps,MSteps=[],[],[],[],[]
    GammaChecks=[] # comparison of pTRM direction acquired and lab field
    Mkeys=['measurement_magn_moment','measurement_magn_volume','measurement_magn_mass','measurement_magnitude']
    rec=datablock[0]
    for key in Mkeys:
        if key in rec.keys() and rec[key]!="":
            momkey=key
            break
# first find all the steps
    for k in range(len(datablock)):
	rec=datablock[k]
        temp=float(rec["treatment_temp"])
        methcodes=[]
        tmp=rec["magic_method_codes"].split(":")
        for meth in tmp:
            methcodes.append(meth.strip())
        if 'LT-T-I' in methcodes and 'LP-TRM' not in methcodes and 'LP-PI-TRM' in methcodes:
            Treat_I.append(temp)
            ISteps.append(k)
            if field=="":field=float(rec["treatment_dc_field"])
            if phi=="":
                phi=float(rec['treatment_dc_field_phi'])
                theta=float(rec['treatment_dc_field_theta'])
# stick  first zero field stuff into first_Z
        if 'LT-NO' in methcodes:
            Treat_Z.append(temp)
            ZSteps.append(k)
        if 'LT-T-Z' in methcodes:
            Treat_Z.append(temp)
            ZSteps.append(k)
        if 'LT-PTRM-Z' in methcodes:
            Treat_PZ.append(temp)
            PZSteps.append(k)
        if 'LT-PTRM-I' in methcodes:
            Treat_PI.append(temp)
            PISteps.append(k)
        if 'LT-PTRM-MD' in methcodes:
            Treat_M.append(temp)
            MSteps.append(k)
        if 'LT-NO' in methcodes:
            dec=float(rec["measurement_dec"])
            inc=float(rec["measurement_inc"])
            str=float(rec[momkey])
            first_I.append([273,0.,0.,0.,1])
            first_Z.append([273,dec,inc,str,1])  # NRM step
    for temp in Treat_I: # look through infield steps and find matching Z step
        if temp in Treat_Z: # found a match
            istep=ISteps[Treat_I.index(temp)]
            irec=datablock[istep]
            methcodes=[]
            tmp=irec["magic_method_codes"].split(":")
            for meth in tmp: methcodes.append(meth.strip())
            brec=datablock[istep-1] # take last record as baseline to subtract
            zstep=ZSteps[Treat_Z.index(temp)]
            zrec=datablock[zstep]
    # sort out first_Z records
            if "LP-PI-TRM-IZ" in methcodes:
                ZI=0
            else:
                ZI=1
            dec=float(zrec["measurement_dec"])
            inc=float(zrec["measurement_inc"])
            str=float(zrec[momkey])
            first_Z.append([temp,dec,inc,str,ZI])
    # sort out first_I records
            idec=float(irec["measurement_dec"])
            iinc=float(irec["measurement_inc"])
            istr=float(irec[momkey])
            X=dir2cart([idec,iinc,istr])
            BL=dir2cart([dec,inc,str])
            I=[]
            for c in range(3): I.append((X[c]-BL[c]))
            if I[2]!=0:
                iDir=cart2dir(I)
                if Zdiff==0:
                    first_I.append([temp,iDir[0],iDir[1],iDir[2],ZI])
                else:
                    first_I.append([temp,0.,0.,I[2],ZI])
                gamma=angle([iDir[0],iDir[1]],[phi,theta])
            else:
                first_I.append([temp,0.,0.,0.,ZI])
                gamma=0.0
# put in Gamma check (infield trm versus lab field)
            if 180.-gamma<gamma:  gamma=180.-gamma
            GammaChecks.append([temp-273.,gamma])
    for temp in Treat_PI: # look through infield steps and find matching Z step
        step=PISteps[Treat_PI.index(temp)]
        rec=datablock[step]
        dec=float(rec["measurement_dec"])
        inc=float(rec["measurement_inc"])
        str=float(rec[momkey])
        brec=datablock[step-1] # take last record as baseline to subtract
        pdec=float(brec["measurement_dec"])
        pinc=float(brec["measurement_inc"])
        pint=float(brec[momkey])
        X=dir2cart([dec,inc,str])
        prevX=dir2cart([pdec,pinc,pint])
        I=[]
        for c in range(3): I.append(X[c]-prevX[c])
        dir1=cart2dir(I)
        if Zdiff==0:
            ptrm_check.append([temp,dir1[0],dir1[1],dir1[2]])
        else:
            ptrm_check.append([temp,0.,0.,I[2]])
# in case there are zero-field pTRM checks (not the SIO way)
    for temp in Treat_PZ:
        step=PZSteps[Treat_PZ.index(temp)]
        rec=datablock[step]
        dec=float(rec["measurement_dec"])
        inc=float(rec["measurement_inc"])
        str=float(rec[momkey])
        brec=datablock[step-1]
        pdec=float(brec["measurement_dec"])
        pinc=float(brec["measurement_inc"])
        pint=float(brec[momkey])
        X=dir2cart([dec,inc,str])
        prevX=dir2cart([pdec,pinc,pint])
        I=[]
        for c in range(3): I.append(X[c]-prevX[c])
        dir2=cart2dir(I)
        zptrm_check.append([temp,dir2[0],dir2[1],dir2[2]])
    ## get pTRM tail checks together -
    for temp in Treat_M:
        step=MSteps[Treat_M.index(temp)] # tail check step - just do a difference in magnitude!
        rec=datablock[step]
#        dec=float(rec["measurement_dec"])
#        inc=float(rec["measurement_inc"])
        str=float(rec[momkey])
        if temp in Treat_Z:
            step=ZSteps[Treat_Z.index(temp)]
            brec=datablock[step]
#        pdec=float(brec["measurement_dec"])
#        pinc=float(brec["measurement_inc"])
            pint=float(brec[momkey])
#        X=dir2cart([dec,inc,str])
#        prevX=dir2cart([pdec,pinc,pint])
#        I=[]
#        for c in range(3):I.append(X[c]-prevX[c])
#        d=cart2dir(I)
#        ptrm_tail.append([temp,d[0],d[1],d[2]])
            ptrm_tail.append([temp,0,0,str-pint])  # difference - if negative, negative tail!
        else:
            print s, '  has a tail check with no first zero field step - check input file! for step',temp-273.
#
# final check
#
    if len(first_Z)!=len(first_I):
               print len(first_Z),len(first_I)
               print " Something wrong with this specimen! Better fix it or delete it "
               raw_input(" press return to acknowledge message")
    araiblock=(first_Z,first_I,ptrm_check,ptrm_tail,zptrm_check,GammaChecks)
    return araiblock,field

def sortmwarai(datablock,exp_type):
    """
     sorts microwave double heating data block in to first_Z, first_I, etc.
    """
    first_Z,first_I,ptrm_check,ptrm_tail,zptrm_check=[],[],[],[],[]
    field,phi,theta="","",""
    POWT_I,POWT_Z,POWT_PZ,POWT_PI,POWT_M=[],[],[],[],[]
    ISteps,ZSteps,PZSteps,PISteps,MSteps=[],[],[],[],[]
    rad=numpy.pi/180.
    ThetaChecks=[] #
    DeltaChecks=[]
    GammaChecks=[]
# first find all the steps
    for k in range(len(datablock)):
        rec=datablock[k]
        powt=int(float(rec["treatment_mw_energy"]))
        methcodes=[]
        tmp=rec["magic_method_codes"].split(":")
        for meth in tmp: methcodes.append(meth.strip())
        if 'LT-M-I' in methcodes and 'LP-MRM' not in methcodes:
            POWT_I.append(powt)
            ISteps.append(k)
            if field=="":field=float(rec['treatment_dc_field'])
            if phi=="":
                phi=float(rec['treatment_dc_field_phi'])
                theta=float(rec['treatment_dc_field_theta'])
        if 'LT-M-Z' in methcodes:
            POWT_Z.append(powt)
            ZSteps.append(k)
        if 'LT-PMRM-Z' in methcodes:
            POWT_PZ.append(powt)
            PZSteps.append(k)
        if 'LT-PMRM-I' in methcodes:
            POWT_PI.append(powt)
            PISteps.append(k)
        if 'LT-PMRM-MD' in methcodes:
            POWT_M.append(powt)
            MSteps.append(k)
        if 'LT-NO' in methcodes:
            dec=float(rec["measurement_dec"])
            inc=float(rec["measurement_inc"])
            str=float(rec["measurement_magn_moment"])
            first_I.append([0,0.,0.,0.,1])
            first_Z.append([0,dec,inc,str,1])  # NRM step
    if exp_type=="LP-PI-M-D":
# now look trough infield steps and  find matching Z step
        for powt in POWT_I:
            if powt in POWT_Z:
                istep=ISteps[POWT_I.index(powt)]
                irec=datablock[istep]
                methcodes=[]
                tmp=irec["magic_method_codes"].split(":")
                for meth in tmp: methcodes.append(meth.strip())
                brec=datablock[istep-1] # take last record as baseline to subtract
                zstep=ZSteps[POWT_Z.index(powt)]
                zrec=datablock[zstep]
    # sort out first_Z records
                if "LP-PI-M-IZ" in methcodes:
                    ZI=0
                else:
                    ZI=1
                dec=float(zrec["measurement_dec"])
                inc=float(zrec["measurement_inc"])
                str=float(zrec["measurement_magn_moment"])
                first_Z.append([powt,dec,inc,str,ZI])
    # sort out first_I records
                idec=float(irec["measurement_dec"])
                iinc=float(irec["measurement_inc"])
                istr=float(irec["measurement_magn_moment"])
                X=dir2cart([idec,iinc,istr])
                BL=dir2cart([dec,inc,str])
                I=[]
                for c in range(3): I.append((X[c]-BL[c]))
                iDir=cart2dir(I)
                first_I.append([powt,iDir[0],iDir[1],iDir[2],ZI])
# put in Gamma check (infield trm versus lab field)
                gamma=angle([iDir[0],iDir[1]],[phi,theta])
                GammaChecks.append([powt,gamma])
    elif exp_type=="LP-PI-M-S":
# find last zero field step before first infield step
        lzrec=datablock[ISteps[0]-1]
        irec=datablock[ISteps[0]]
        ndec=float(lzrec["measurement_dec"])
        ninc=float(lzrec["measurement_inc"])
        nstr=float(lzrec["measurement_magn_moment"])
        NRM=dir2cart([ndec,ninc,nstr])
        fdec=float(irec["treatment_dc_field_phi"])
        finc=float(irec["treatment_dc_field_theta"])
        Flab=dir2cart([fdec,finc,1.])
        for step in ISteps:
            irec=datablock[step]
            rdec=float(irec["measurement_dec"])
            rinc=float(irec["measurement_inc"])
            rstr=float(irec["measurement_magn_moment"])
            theta1=angle([ndec,ninc],[rdec,rinc])
            theta2=angle([rdec,rinc],[fdec,finc])
            powt=int(float(irec["treatment_mw_energy"]))
            ThetaChecks.append([powt,theta1+theta2])
            p=(180.-(theta1+theta2))
            nstr=rstr*(numpy.sin(theta2*rad)/numpy.sin(p*rad))
            tmstr=rstr*(numpy.sin(theta1*rad)/numpy.sin(p*rad))
            first_Z.append([powt,ndec,ninc,nstr,1])
            first_I.append([powt,dec,inc,tmstr,1])
# check if zero field steps are parallel to assumed NRM
        for step in ZSteps:
            zrec=datablock[step]
            powt=int(float(zrec["treatment_mw_energy"]))
            zdec=float(zrec["measurement_dec"])
            zinc=float(zrec["measurement_inc"])
            delta=angle([ndec,ninc],[zdec,zinc])
            DeltaChecks.append([powt,delta])
    # get pTRMs together - take previous record and subtract
    for powt in POWT_PI:
        step=PISteps[POWT_PI.index(powt)]
        rec=datablock[step]
        dec=float(rec["measurement_dec"])
        inc=float(rec["measurement_inc"])
        str=float(rec["measurement_magn_moment"])
        brec=datablock[step-1] # take last record as baseline to subtract
        pdec=float(brec["measurement_dec"])
        pinc=float(brec["measurement_inc"])
        pint=float(brec["measurement_magn_moment"])
        X=dir2cart([dec,inc,str])
        prevX=dir2cart([pdec,pinc,pint])
        I=[]
        for c in range(3): I.append(X[c]-prevX[c])
        dir1=cart2dir(I)
        ptrm_check.append([powt,dir1[0],dir1[1],dir1[2]])
    ## get zero field pTRM  checks together
    for powt in POWT_PZ:
        step=PZSteps[POWT_PZ.index(powt)]
        rec=datablock[step]
        dec=float(rec["measurement_dec"])
        inc=float(rec["measurement_inc"])
        str=float(rec["measurement_magn_moment"])
        brec=datablock[step-1]
        pdec=float(brec["measurement_dec"])
        pinc=float(brec["measurement_inc"])
        pint=float(brec["measurement_magn_moment"])
        X=dir2cart([dec,inc,str])
        prevX=dir2cart([pdec,pinc,pint])
        I=[]
        for c in range(3): I.append(X[c]-prevX[c])
        dir2=cart2dir(I)
        zptrm_check.append([powt,dir2[0],dir2[1],dir2[2]])
    ## get pTRM tail checks together -
    for powt in POWT_M:
        step=MSteps[POWT_M.index(powt)] # tail check step
        rec=datablock[step]
#        dec=float(rec["measurement_dec"])
#        inc=float(rec["measurement_inc"])
        str=float(rec["measurement_magn_moment"])
        step=ZSteps[POWT_Z.index(powt)]
        brec=datablock[step]
#        pdec=float(brec["measurement_dec"])
#        pinc=float(brec["measurement_inc"])
        pint=float(brec["measurement_magn_moment"])
#        X=dir2cart([dec,inc,str])
#        prevX=dir2cart([pdec,pinc,pint])
#        I=[]
#        for c in range(3):I.append(X[c]-prevX[c])
#        d=cart2dir(I)
 #       ptrm_tail.append([powt,d[0],d[1],d[2]])
        ptrm_tail.append([powt,0,0,str-pint])  # just do absolute magnitude difference # not vector diff
    #  check
    #
        if len(first_Z)!=len(first_I):
                   print len(first_Z),len(first_I)
                   print " Something wrong with this specimen! Better fix it or delete it "
                   raw_input(" press return to acknowledge message")
                   print MaxRec
    araiblock=(first_Z,first_I,ptrm_check,ptrm_tail,zptrm_check,GammaChecks,ThetaChecks,DeltaChecks)
    return araiblock,field

    #
def doigrf(long,lat,alt,date,**kwargs):
    """
    called with doigrf(long,lat,alt,date,**kwargs)
#       calculates the interpolated (<2010) or extrapolated (>2010) main field and
#       secular variation coefficients and passes these to the Malin and Barraclough
#       routine to calculate the IGRF field. dgrf coefficients for 1945 to 2005, igrf for pre 1945 and post 2010
#       from http://www.ngdc.noaa.gov/IAGA/vmod/igrf.html
#
#      for dates prior to between 1900 and 1600, this program uses coefficients from the GUFM1 model of Jackson et al. 2000
#      prior to that, it uses either arch3k or one of the cals models
#
#
#       input:
#       long  = east longitude in degrees (0 to 360 or -180 to 180)
#       lat   = latitude in degrees (-90 to 90)
#       alt   = height above mean sea level in km (itype = 1 assumed)
#       date  = Required date in years and decimals of a year (A.D.)
# Output:
#       x     = north component of the magnetic force in nT
#       y     = east component of the magnetic force in nT
#       z     = downward component of the magnetic force in nT
#       f     = total magnetic force in nT
#
#       To check the results you can run the interactive program at the NGDC
#        http://www.ngdc.noaa.gov/geomagmodels/IGRFWMM.jsp
    """

#
#
    gh,sv=[],[]
    colat = 90.-lat
#! convert to colatitude for MB routine
    if long>0: long=long+360.
# ensure all positive east longitudes
    itype = 1
    models,igrf12coeffs=get_igrf12()
    if 'mod' in kwargs.keys():
        if kwargs['mod']=='arch3k':
            psvmodels,psvcoeffs=get_arch3k() # use ARCH3k coefficients
        elif kwargs['mod']=='cals3k':
            psvmodels,psvcoeffs=get_cals3k() # default: use CALS3K_4b coefficients between -1000,1940
        elif kwargs['mod']=='pfm9k':
            psvmodels,psvcoeffs=get_pfm9k() #  use PFM9k (Nilsson et al., 2014), coefficients from -7000 to 1900
        else:
            psvmodels,psvcoeffs=get_cals10k() # use prior to -1000, back to -8000
# use geodetic coordinates
    if 'models' in kwargs:
        if 'mod' in kwargs.keys():
            return psvmodels,psvcoeffs
        else:
            return models,igrf12coeffs
    if date<-8000:
        print 'too old'
        sys.exit()
    if date<-1000:
        if kwargs['mod']=='pfm9k':
            incr=10
        else:
            incr=50
        model=date-date%incr
        gh=psvcoeffs[psvmodels.index(int(model))]
        sv=(psvcoeffs[psvmodels.index(int(model+incr))]-gh)/float(incr)
        x,y,z,f=magsyn(gh,sv,model,date,itype,alt,colat,long)
    elif date<1900:
        if kwargs['mod']=='cals10k':
            incr=50
        else:
            incr=10
        model=date-date%incr
        gh=psvcoeffs[psvmodels.index(model)]
        if model+incr<1900:
            sv=(psvcoeffs[psvmodels.index(model+incr)]-gh)/float(incr)
        else:
            field2=igrf12coeffs[models.index(1940)][0:120]
            sv=(field2-gh)/float(1940-model)
        x,y,z,f=magsyn(gh,sv,model,date,itype,alt,colat,long)
    else:
        model=date-date%5
        if date<2015:
            gh=igrf12coeffs[models.index(model)]
            sv=(igrf12coeffs[models.index(model+5)]-gh)/5.
            x,y,z,f=magsyn(gh,sv,model,date,itype,alt,colat,long)
        else:
            gh=igrf12coeffs[models.index(2015)]
            sv=igrf12coeffs[models.index(2015.20)]
            x,y,z,f=magsyn(gh,sv,model,date,itype,alt,colat,long)
    if 'coeffs' in kwargs.keys():
        return gh
    else:
        return x,y,z,f
#
def get_igrf12():
    models= [1900, 1905, 1910, 1915, 1920, 1925, 1930, 1935, 1940, 1945, 1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2015.20]
    coeffs=numpy.array([[-31543, -2298, 5922, -677, 2905, -1061, 924, 1121, 1022, -1469, -330, 1256, 3, 572, 523, 876, 628, 195, 660, -69, -361, -210, 134, -75, -184, 328, -210, 264, 53, 5, -33, -86, -124, -16, 3, 63, 61, -9, -11, 83, -217, 2, -58, -35, 59, 36, -90, -69, 70, -55, -45, 0, -13, 34, -10, -41, -1, -21, 28, 18, -12, 6, -22, 11, 8, 8, -4, -14, -9, 7, 1, -13, 2, 5, -9, 16, 5, -5, 8, -18, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 8, 2, 10, -1, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 2, 4, 2, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-31464, -2298, 5909, -728, 2928, -1086, 1041, 1065, 1037, -1494, -357, 1239, 34, 635, 480, 880, 643, 203, 653, -77, -380, -201, 146, -65, -192, 328, -193, 259, 56, -1, -32, -93, -125, -26, 11, 62, 60, -7, -11, 86, -221, 4, -57, -32, 57, 32, -92, -67, 70, -54, -46, 0, -14, 33, -11, -41, 0, -20, 28, 18, -12, 6, -22, 11, 8, 8, -4, -15, -9, 7, 1, -13, 2, 5, -8, 16, 5, -5, 8, -18, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 8, 2, 10, 0, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 2, 4, 2, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-31354, -2297, 5898, -769, 2948, -1128, 1176, 1000, 1058, -1524, -389, 1223, 62, 705, 425, 884, 660, 211, 644, -90, -400, -189, 160, -55, -201, 327, -172, 253, 57, -9, -33, -102, -126, -38, 21, 62, 58, -5, -11, 89, -224, 5, -54, -29, 54, 28, -95, -65, 71, -54, -47, 1, -14, 32, -12, -40, 1, -19, 28, 18, -13, 6, -22, 11, 8, 8, -4, -15, -9, 6, 1, -13, 2, 5, -8, 16, 5, -5, 8, -18, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 8, 2, 10, 0, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 2, 4, 2, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-31212, -2306, 5875, -802, 2956, -1191, 1309, 917, 1084, -1559, -421, 1212, 84, 778, 360, 887, 678, 218, 631, -109, -416, -173, 178, -51, -211, 327, -148, 245, 58, -16, -34, -111, -126, -51, 32, 61, 57, -2, -10, 93, -228, 8, -51, -26, 49, 23, -98, -62, 72, -54, -48, 2, -14, 31, -12, -38, 2, -18, 28, 19, -15, 6, -22, 11, 8, 8, -4, -15, -9, 6, 2, -13, 3, 5, -8, 16, 6, -5, 8, -18, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 8, 2, 10, 0, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 1, 4, 2, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-31060, -2317, 5845, -839, 2959, -1259, 1407, 823, 1111, -1600, -445, 1205, 103, 839, 293, 889, 695, 220, 616, -134, -424, -153, 199, -57, -221, 326, -122, 236, 58, -23, -38, -119, -125, -62, 43, 61, 55, 0, -10, 96, -233, 11, -46, -22, 44, 18, -101, -57, 73, -54, -49, 2, -14, 29, -13, -37, 4, -16, 28, 19, -16, 6, -22, 11, 7, 8, -3, -15, -9, 6, 2, -14, 4, 5, -7, 17, 6, -5, 8, -19, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 9, 2, 10, 0, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 1, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30926, -2318, 5817, -893, 2969, -1334, 1471, 728, 1140, -1645, -462, 1202, 119, 881, 229, 891, 711, 216, 601, -163, -426, -130, 217, -70, -230, 326, -96, 226, 58, -28, -44, -125, -122, -69, 51, 61, 54, 3, -9, 99, -238, 14, -40, -18, 39, 13, -103, -52, 73, -54, -50, 3, -14, 27, -14, -35, 5, -14, 29, 19, -17, 6, -21, 11, 7, 8, -3, -15, -9, 6, 2, -14, 4, 5, -7, 17, 7, -5, 8, -19, 8, 10, -20, 1, 14, -11, 5, 12, -3, 1, -2, -2, 9, 2, 10, 0, -2, -1, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 1, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30805, -2316, 5808, -951, 2980, -1424, 1517, 644, 1172, -1692, -480, 1205, 133, 907, 166, 896, 727, 205, 584, -195, -422, -109, 234, -90, -237, 327, -72, 218, 60, -32, -53, -131, -118, -74, 58, 60, 53, 4, -9, 102, -242, 19, -32, -16, 32, 8, -104, -46, 74, -54, -51, 4, -15, 25, -14, -34, 6, -12, 29, 18, -18, 6, -20, 11, 7, 8, -3, -15, -9, 5, 2, -14, 5, 5, -6, 18, 8, -5, 8, -19, 8, 10, -20, 1, 14, -12, 5, 12, -3, 1, -2, -2, 9, 3, 10, 0, -2, -2, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -2, 1, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30715, -2306, 5812, -1018, 2984, -1520, 1550, 586, 1206, -1740, -494, 1215, 146, 918, 101, 903, 744, 188, 565, -226, -415, -90, 249, -114, -241, 329, -51, 211, 64, -33, -64, -136, -115, -76, 64, 59, 53, 4, -8, 104, -246, 25, -25, -15, 25, 4, -106, -40, 74, -53, -52, 4, -17, 23, -14, -33, 7, -11, 29, 18, -19, 6, -19, 11, 7, 8, -3, -15, -9, 5, 1, -15, 6, 5, -6, 18, 8, -5, 7, -19, 8, 10, -20, 1, 15, -12, 5, 11, -3, 1, -3, -2, 9, 3, 11, 0, -2, -2, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -1, 2, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30654, -2292, 5821, -1106, 2981, -1614, 1566, 528, 1240, -1790, -499, 1232, 163, 916, 43, 914, 762, 169, 550, -252, -405, -72, 265, -141, -241, 334, -33, 208, 71, -33, -75, -141, -113, -76, 69, 57, 54, 4, -7, 105, -249, 33, -18, -15, 18, 0, -107, -33, 74, -53, -52, 4, -18, 20, -14, -31, 7, -9, 29, 17, -20, 5, -19, 11, 7, 8, -3, -14, -10, 5, 1, -15, 6, 5, -5, 19, 9, -5, 7, -19, 8, 10, -21, 1, 15, -12, 5, 11, -3, 1, -3, -2, 9, 3, 11, 1, -2, -2, 2, -3, -4, 2, 2, 1, -5, 2, -2, 6, 6, -4, 4, 0, 0, -1, 2, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30594, -2285, 5810, -1244, 2990, -1702, 1578, 477, 1282, -1834, -499, 1255, 186, 913, -11, 944, 776, 144, 544, -276, -421, -55, 304, -178, -253, 346, -12, 194, 95, -20, -67, -142, -119, -82, 82, 59, 57, 6, 6, 100, -246, 16, -25, -9, 21, -16, -104, -39, 70, -40, -45, 0, -18, 0, 2, -29, 6, -10, 28, 15, -17, 29, -22, 13, 7, 12, -8, -21, -5, -12, 9, -7, 7, 2, -10, 18, 7, 3, 2, -11, 5, -21, -27, 1, 17, -11, 29, 3, -9, 16, 4, -3, 9, -4, 6, -3, 1, -4, 8, -3, 11, 5, 1, 1, 2, -20, -5, -1, -1, -6, 8, 6, -1, -4, -3, -2, 5, 0, -2, -2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30554, -2250, 5815, -1341, 2998, -1810, 1576, 381, 1297, -1889, -476, 1274, 206, 896, -46, 954, 792, 136, 528, -278, -408, -37, 303, -210, -240, 349, 3, 211, 103, -20, -87, -147, -122, -76, 80, 54, 57, -1, 4, 99, -247, 33, -16, -12, 12, -12, -105, -30, 65, -55, -35, 2, -17, 1, 0, -40, 10, -7, 36, 5, -18, 19, -16, 22, 15, 5, -4, -22, -1, 0, 11, -21, 15, -8, -13, 17, 5, -4, -1, -17, 3, -7, -24, -1, 19, -25, 12, 10, 2, 5, 2, -5, 8, -2, 8, 3, -11, 8, -7, -8, 4, 13, -1, -2, 13, -10, -4, 2, 4, -3, 12, 6, 3, -3, 2, 6, 10, 11, 3, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30500, -2215, 5820, -1440, 3003, -1898, 1581, 291, 1302, -1944, -462, 1288, 216, 882, -83, 958, 796, 133, 510, -274, -397, -23, 290, -230, -229, 360, 15, 230, 110, -23, -98, -152, -121, -69, 78, 47, 57, -9, 3, 96, -247, 48, -8, -16, 7, -12, -107, -24, 65, -56, -50, 2, -24, 10, -4, -32, 8, -11, 28, 9, -20, 18, -18, 11, 9, 10, -6, -15, -14, 5, 6, -23, 10, 3, -7, 23, 6, -4, 9, -13, 4, 9, -11, -4, 12, -5, 7, 2, 6, 4, -2, 1, 10, 2, 7, 2, -6, 5, 5, -3, -5, -4, -1, 0, 2, -8, -3, -2, 7, -4, 4, 1, -2, -3, 6, 7, -2, -1, 0, -3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30421, -2169, 5791, -1555, 3002, -1967, 1590, 206, 1302, -1992, -414, 1289, 224, 878, -130, 957, 800, 135, 504, -278, -394, 3, 269, -255, -222, 362, 16, 242, 125, -26, -117, -156, -114, -63, 81, 46, 58, -10, 1, 99, -237, 60, -1, -20, -2, -11, -113, -17, 67, -56, -55, 5, -28, 15, -6, -32, 7, -7, 23, 17, -18, 8, -17, 15, 6, 11, -4, -14, -11, 7, 2, -18, 10, 4, -5, 23, 10, 1, 8, -20, 4, 6, -18, 0, 12, -9, 2, 1, 0, 4, -3, -1, 9, -2, 8, 3, 0, -1, 5, 1, -3, 4, 4, 1, 0, 0, -1, 2, 4, -5, 6, 1, 1, -1, -1, 6, 2, 0, 0, -7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30334, -2119, 5776, -1662, 2997, -2016, 1594, 114, 1297, -2038, -404, 1292, 240, 856, -165, 957, 804, 148, 479, -269, -390, 13, 252, -269, -219, 358, 19, 254, 128, -31, -126, -157, -97, -62, 81, 45, 61, -11, 8, 100, -228, 68, 4, -32, 1, -8, -111, -7, 75, -57, -61, 4, -27, 13, -2, -26, 6, -6, 26, 13, -23, 1, -12, 13, 5, 7, -4, -12, -14, 9, 0, -16, 8, 4, -1, 24, 11, -3, 4, -17, 8, 10, -22, 2, 15, -13, 7, 10, -4, -1, -5, -1, 10, 5, 10, 1, -4, -2, 1, -2, -3, 2, 2, 1, -5, 2, -2, 6, 4, -4, 4, 0, 0, -2, 2, 3, 2, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30220, -2068, 5737, -1781, 3000, -2047, 1611, 25, 1287, -2091, -366, 1278, 251, 838, -196, 952, 800, 167, 461, -266, -395, 26, 234, -279, -216, 359, 26, 262, 139, -42, -139, -160, -91, -56, 83, 43, 64, -12, 15, 100, -212, 72, 2, -37, 3, -6, -112, 1, 72, -57, -70, 1, -27, 14, -4, -22, 8, -2, 23, 13, -23, -2, -11, 14, 6, 7, -2, -15, -13, 6, -3, -17, 5, 6, 0, 21, 11, -6, 3, -16, 8, 10, -21, 2, 16, -12, 6, 10, -4, -1, -5, 0, 10, 3, 11, 1, -2, -1, 1, -3, -3, 1, 2, 1, -5, 3, -1, 4, 6, -4, 4, 0, 1, -1, 0, 3, 3, 1, -1, -4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-30100, -2013, 5675, -1902, 3010, -2067, 1632, -68, 1276, -2144, -333, 1260, 262, 830, -223, 946, 791, 191, 438, -265, -405, 39, 216, -288, -218, 356, 31, 264, 148, -59, -152, -159, -83, -49, 88, 45, 66, -13, 28, 99, -198, 75, 1, -41, 6, -4, -111, 11, 71, -56, -77, 1, -26, 16, -5, -14, 10, 0, 22, 12, -23, -5, -12, 14, 6, 6, -1, -16, -12, 4, -8, -19, 4, 6, 0, 18, 10, -10, 1, -17, 7, 10, -21, 2, 16, -12, 7, 10, -4, -1, -5, -1, 10, 4, 11, 1, -3, -2, 1, -3, -3, 1, 2, 1, -5, 3, -2, 4, 5, -4, 4, -1, 1, -1, 0, 3, 3, 1, -1, -5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-29992, -1956, 5604, -1997, 3027, -2129, 1663, -200, 1281, -2180, -336, 1251, 271, 833, -252, 938, 782, 212, 398, -257, -419, 53, 199, -297, -218, 357, 46, 261, 150, -74, -151, -162, -78, -48, 92, 48, 66, -15, 42, 93, -192, 71, 4, -43, 14, -2, -108, 17, 72, -59, -82, 2, -27, 21, -5, -12, 16, 1, 18, 11, -23, -2, -10, 18, 6, 7, 0, -18, -11, 4, -7, -22, 4, 9, 3, 16, 6, -13, -1, -15, 5, 10, -21, 1, 16, -12, 9, 9, -5, -3, -6, -1, 9, 7, 10, 2, -6, -5, 2, -4, -4, 1, 2, 0, -5, 3, -2, 6, 5, -4, 3, 0, 1, -1, 2, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-29873, -1905, 5500, -2072, 3044, -2197, 1687, -306, 1296, -2208, -310, 1247, 284, 829, -297, 936, 780, 232, 361, -249, -424, 69, 170, -297, -214, 355, 47, 253, 150, -93, -154, -164, -75, -46, 95, 53, 65, -16, 51, 88, -185, 69, 4, -48, 16, -1, -102, 21, 74, -62, -83, 3, -27, 24, -2, -6, 20, 4, 17, 10, -23, 0, -7, 21, 6, 8, 0, -19, -11, 5, -9, -23, 4, 11, 4, 14, 4, -15, -4, -11, 5, 10, -21, 1, 15, -12, 9, 9, -6, -3, -6, -1, 9, 7, 9, 1, -7, -5, 2, -4, -4, 1, 3, 0, -5, 3, -2, 6, 5, -4, 3, 0, 1, -1, 2, 4, 3, 0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-29775, -1848, 5406, -2131, 3059, -2279, 1686, -373, 1314, -2239, -284, 1248, 293, 802, -352, 939, 780, 247, 325, -240, -423, 84, 141, -299, -214, 353, 46, 245, 154, -109, -153, -165, -69, -36, 97, 61, 65, -16, 59, 82, -178, 69, 3, -52, 18, 1, -96, 24, 77, -64, -80, 2, -26, 26, 0, -1, 21, 5, 17, 9, -23, 0, -4, 23, 5, 10, -1, -19, -10, 6, -12, -22, 3, 12, 4, 12, 2, -16, -6, -10, 4, 9, -20, 1, 15, -12, 11, 9, -7, -4, -7, -2, 9, 7, 8, 1, -7, -6, 2, -3, -4, 2, 2, 1, -5, 3, -2, 6, 4, -4, 3, 0, 1, -2, 3, 3, 3, -1, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-29692, -1784, 5306, -2200, 3070, -2366, 1681, -413, 1335, -2267, -262, 1249, 302, 759, -427, 940, 780, 262, 290, -236, -418, 97, 122, -306, -214, 352, 46, 235, 165, -118, -143, -166, -55, -17, 107, 68, 67, -17, 68, 72, -170, 67, -1, -58, 19, 1, -93, 36, 77, -72, -69, 1, -25, 28, 4, 5, 24, 4, 17, 8, -24, -2, -6, 25, 6, 11, -6, -21, -9, 8, -14, -23, 9, 15, 6, 11, -5, -16, -7, -4, 4, 9, -20, 3, 15, -10, 12, 8, -6, -8, -8, -1, 8, 10, 5, -2, -8, -8, 3, -3, -6, 1, 2, 0, -4, 4, -1, 5, 4, -5, 2, -1, 2, -2, 5, 1, 1, -2, 0, -7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [-29619.400000000001, -1728.2, 5186.1000000000004, -2267.6999999999998, 3068.4000000000001, -2481.5999999999999, 1670.9000000000001, -458.0, 1339.5999999999999, -2288.0, -227.59999999999999, 1252.0999999999999, 293.39999999999998, 714.5, -491.10000000000002, 932.29999999999995, 786.79999999999995, 272.60000000000002, 250.0, -231.90000000000001, -403.0, 119.8, 111.3, -303.80000000000001, -218.80000000000001, 351.39999999999998, 43.799999999999997, 222.30000000000001, 171.90000000000001, -130.40000000000001, -133.09999999999999, -168.59999999999999, -39.299999999999997, -12.9, 106.3, 72.299999999999997, 68.200000000000003, -17.399999999999999, 74.200000000000003, 63.700000000000003, -160.90000000000001, 65.099999999999994, -5.9000000000000004, -61.200000000000003, 16.899999999999999, 0.69999999999999996, -90.400000000000006, 43.799999999999997, 79.0, -74.0, -64.599999999999994, 0.0, -24.199999999999999, 33.299999999999997, 6.2000000000000002, 9.0999999999999996, 24.0, 6.9000000000000004, 14.800000000000001, 7.2999999999999998, -25.399999999999999, -1.2, -5.7999999999999998, 24.399999999999999, 6.5999999999999996, 11.9, -9.1999999999999993, -21.5, -7.9000000000000004, 8.5, -16.600000000000001, -21.5, 9.0999999999999996, 15.5, 7.0, 8.9000000000000004, -7.9000000000000004, -14.9, -7.0, -2.1000000000000001, 5.0, 9.4000000000000004, -19.699999999999999, 3.0, 13.4, -8.4000000000000004, 12.5, 6.2999999999999998, -6.2000000000000002, -8.9000000000000004, -8.4000000000000004, -1.5, 8.4000000000000004, 9.3000000000000007, 3.7999999999999998, -4.2999999999999998, -8.1999999999999993, -8.1999999999999993, 4.7999999999999998, -2.6000000000000001, -6.0, 1.7, 1.7, 0.0, -3.1000000000000001, 4.0, -0.5, 4.9000000000000004, 3.7000000000000002, -5.9000000000000004, 1.0, -1.2, 2.0, -2.8999999999999999, 4.2000000000000002, 0.20000000000000001, 0.29999999999999999, -2.2000000000000002, -1.1000000000000001, -7.4000000000000004, 2.7000000000000002, -1.7, 0.10000000000000001, -1.8999999999999999, 1.3, 1.5, -0.90000000000000002, -0.10000000000000001, -2.6000000000000001, 0.10000000000000001, 0.90000000000000002, -0.69999999999999996, -0.69999999999999996, 0.69999999999999996, -2.7999999999999998, 1.7, -0.90000000000000002, 0.10000000000000001, -1.2, 1.2, -1.8999999999999999, 4.0, -0.90000000000000002, -2.2000000000000002, -0.29999999999999999, -0.40000000000000002, 0.20000000000000001, 0.29999999999999999, 0.90000000000000002, 2.5, -0.20000000000000001, -2.6000000000000001, 0.90000000000000002, 0.69999999999999996, -0.5, 0.29999999999999999, 0.29999999999999999, 0.0, -0.29999999999999999, 0.0, -0.40000000000000002, 0.29999999999999999, -0.10000000000000001, -0.90000000000000002, -0.20000000000000001, -0.40000000000000002, -0.40000000000000002, 0.80000000000000004, -0.20000000000000001, -0.90000000000000002, -0.90000000000000002, 0.29999999999999999, 0.20000000000000001, 0.10000000000000001, 1.8, -0.40000000000000002, -0.40000000000000002, 1.3, -1.0, -0.40000000000000002, -0.10000000000000001, 0.69999999999999996, 0.69999999999999996, -0.40000000000000002, 0.29999999999999999, 0.29999999999999999, 0.59999999999999998, -0.10000000000000001, 0.29999999999999999, 0.40000000000000002, -0.20000000000000001, 0.0, -0.5, 0.10000000000000001, -0.90000000000000002], [-29554.630000000001, -1669.05, 5077.9899999999998, -2337.2399999999998, 3047.6900000000001, -2594.5, 1657.76, -515.42999999999995, 1336.3, -2305.8299999999999, -198.86000000000001, 1246.3900000000001, 269.72000000000003, 672.50999999999999, -524.72000000000003, 920.54999999999995, 797.96000000000004, 282.06999999999999, 210.65000000000001, -225.22999999999999, -379.86000000000001, 145.15000000000001, 100.0, -305.36000000000001, -227.0, 354.41000000000003, 42.719999999999999, 208.94999999999999, 180.25, -136.53999999999999, -123.45, -168.05000000000001, -19.57, -13.550000000000001, 103.84999999999999, 73.599999999999994, 69.560000000000002, -20.329999999999998, 76.739999999999995, 54.75, -151.34, 63.630000000000003, -14.58, -63.530000000000001, 14.58, 0.23999999999999999, -86.359999999999999, 50.939999999999998, 79.879999999999995, -74.459999999999994, -61.140000000000001, -1.6499999999999999, -22.57, 38.729999999999997, 6.8200000000000003, 12.300000000000001, 25.350000000000001, 9.3699999999999992, 10.93, 5.4199999999999999, -26.32, 1.9399999999999999, -4.6399999999999997, 24.800000000000001, 7.6200000000000001, 11.199999999999999, -11.73, -20.879999999999999, -6.8799999999999999, 9.8300000000000001, -18.109999999999999, -19.710000000000001, 10.17, 16.219999999999999, 9.3599999999999994, 7.6100000000000003, -11.25, -12.76, -4.8700000000000001, -0.059999999999999998, 5.5800000000000001, 9.7599999999999998, -20.109999999999999, 3.5800000000000001, 12.69, -6.9400000000000004, 12.67, 5.0099999999999998, -6.7199999999999998, -10.76, -8.1600000000000001, -1.25, 8.0999999999999996, 8.7599999999999998, 2.9199999999999999, -6.6600000000000001, -7.7300000000000004, -9.2200000000000006, 6.0099999999999998, -2.1699999999999999, -6.1200000000000001, 2.1899999999999999, 1.4199999999999999, 0.10000000000000001, -2.3500000000000001, 4.46, -0.14999999999999999, 4.7599999999999998, 3.0600000000000001, -6.5800000000000001, 0.28999999999999998, -1.01, 2.0600000000000001, -3.4700000000000002, 3.77, -0.85999999999999999, -0.20999999999999999, -2.3100000000000001, -2.0899999999999999, -7.9299999999999997, 2.9500000000000002, -1.6000000000000001, 0.26000000000000001, -1.8799999999999999, 1.4399999999999999, 1.4399999999999999, -0.77000000000000002, -0.31, -2.27, 0.28999999999999998, 0.90000000000000002, -0.79000000000000004, -0.57999999999999996, 0.53000000000000003, -2.6899999999999999, 1.8, -1.0800000000000001, 0.16, -1.5800000000000001, 0.95999999999999996, -1.8999999999999999, 3.9900000000000002, -1.3899999999999999, -2.1499999999999999, -0.28999999999999998, -0.55000000000000004, 0.20999999999999999, 0.23000000000000001, 0.89000000000000001, 2.3799999999999999, -0.38, -2.6299999999999999, 0.95999999999999996, 0.60999999999999999, -0.29999999999999999, 0.40000000000000002, 0.46000000000000002, 0.01, -0.34999999999999998, 0.02, -0.35999999999999999, 0.28000000000000003, 0.080000000000000002, -0.87, -0.48999999999999999, -0.34000000000000002, -0.080000000000000002, 0.88, -0.16, -0.88, -0.76000000000000001, 0.29999999999999999, 0.33000000000000002, 0.28000000000000003, 1.72, -0.42999999999999999, -0.54000000000000004, 1.1799999999999999, -1.0700000000000001, -0.37, -0.040000000000000001, 0.75, 0.63, -0.26000000000000001, 0.20999999999999999, 0.34999999999999998, 0.53000000000000003, -0.050000000000000003, 0.38, 0.40999999999999998, -0.22, -0.10000000000000001, -0.56999999999999995, -0.17999999999999999, -0.81999999999999995], [-29496.57, -1586.4200000000001, 4944.2600000000002, -2396.0599999999999, 3026.3400000000001, -2708.54, 1668.1700000000001, -575.73000000000002, 1339.8499999999999, -2326.54, -160.40000000000001, 1232.0999999999999, 251.75, 633.73000000000002, -537.02999999999997, 912.65999999999997, 808.97000000000003, 286.48000000000002, 166.58000000000001, -211.03, -356.82999999999998, 164.46000000000001, 89.400000000000006, -309.72000000000003, -230.87, 357.29000000000002, 44.579999999999998, 200.25999999999999, 189.00999999999999, -141.05000000000001, -118.06, -163.16999999999999, -0.01, -8.0299999999999994, 101.04000000000001, 72.780000000000001, 68.689999999999998, -20.899999999999999, 75.920000000000002, 44.18, -141.40000000000001, 61.539999999999999, -22.829999999999998, -66.260000000000005, 13.1, 3.02, -78.090000000000003, 55.399999999999999, 80.439999999999998, -75.0, -57.799999999999997, -4.5499999999999998, -21.199999999999999, 45.240000000000002, 6.54, 14.0, 24.960000000000001, 10.460000000000001, 7.0300000000000002, 1.6399999999999999, -27.609999999999999, 4.9199999999999999, -3.2799999999999998, 24.41, 8.2100000000000009, 10.84, -14.5, -20.030000000000001, -5.5899999999999999, 11.83, -19.34, -17.41, 11.609999999999999, 16.710000000000001, 10.85, 6.96, -14.050000000000001, -10.74, -3.54, 1.6399999999999999, 5.5, 9.4499999999999993, -20.539999999999999, 3.4500000000000002, 11.51, -5.2699999999999996, 12.75, 3.1299999999999999, -7.1399999999999997, -12.380000000000001, -7.4199999999999999, -0.76000000000000001, 7.9699999999999998, 8.4299999999999997, 2.1400000000000001, -8.4199999999999999, -6.0800000000000001, -10.08, 7.0099999999999998, -1.9399999999999999, -6.2400000000000002, 2.73, 0.89000000000000001, -0.10000000000000001, -1.0700000000000001, 4.71, -0.16, 4.4400000000000004, 2.4500000000000002, -7.2199999999999998, -0.33000000000000002, -0.95999999999999996, 2.1299999999999999, -3.9500000000000002, 3.0899999999999999, -1.99, -1.03, -1.97, -2.7999999999999998, -8.3100000000000005, 3.0499999999999998, -1.48, 0.13, -2.0299999999999998, 1.6699999999999999, 1.6499999999999999, -0.66000000000000003, -0.51000000000000001, -1.76, 0.54000000000000004, 0.84999999999999998, -0.79000000000000004, -0.39000000000000001, 0.37, -2.5099999999999998, 1.79, -1.27, 0.12, -2.1099999999999999, 0.75, -1.9399999999999999, 3.75, -1.8600000000000001, -2.1200000000000001, -0.20999999999999999, -0.87, 0.29999999999999999, 0.27000000000000002, 1.04, 2.1299999999999999, -0.63, -2.4900000000000002, 0.94999999999999996, 0.48999999999999999, -0.11, 0.58999999999999997, 0.52000000000000002, 0.0, -0.39000000000000001, 0.13, -0.37, 0.27000000000000002, 0.20999999999999999, -0.85999999999999999, -0.77000000000000002, -0.23000000000000001, 0.040000000000000001, 0.87, -0.089999999999999997, -0.89000000000000001, -0.87, 0.31, 0.29999999999999999, 0.41999999999999998, 1.6599999999999999, -0.45000000000000001, -0.58999999999999997, 1.0800000000000001, -1.1399999999999999, -0.31, -0.070000000000000007, 0.78000000000000003, 0.54000000000000004, -0.17999999999999999, 0.10000000000000001, 0.38, 0.48999999999999999, 0.02, 0.44, 0.41999999999999998, -0.25, -0.26000000000000001, -0.53000000000000003, -0.26000000000000001, -0.79000000000000004], [-29442.0, -1501.0, 4797.1000000000004, -2445.0999999999999, 3012.9000000000001, -2845.5999999999999, 1676.7, -641.89999999999998, 1350.7, -2352.3000000000002, -115.3, 1225.5999999999999, 244.90000000000001, 582.0, -538.39999999999998, 907.60000000000002, 813.70000000000005, 283.30000000000001, 120.40000000000001, -188.69999999999999, -334.89999999999998, 180.90000000000001, 70.400000000000006, -329.5, -232.59999999999999, 360.10000000000002, 47.299999999999997, 192.40000000000001, 197.0, -140.90000000000001, -119.3, -157.5, 16.0, 4.0999999999999996, 100.2, 70.0, 67.700000000000003, -20.800000000000001, 72.700000000000003, 33.200000000000003, -129.90000000000001, 58.899999999999999, -28.899999999999999, -66.700000000000003, 13.199999999999999, 7.2999999999999998, -70.900000000000006, 62.600000000000001, 81.599999999999994, -76.099999999999994, -54.100000000000001, -6.7999999999999998, -19.5, 51.799999999999997, 5.7000000000000002, 15.0, 24.399999999999999, 9.4000000000000004, 3.3999999999999999, -2.7999999999999998, -27.399999999999999, 6.7999999999999998, -2.2000000000000002, 24.199999999999999, 8.8000000000000007, 10.1, -16.899999999999999, -18.300000000000001, -3.2000000000000002, 13.300000000000001, -20.600000000000001, -14.6, 13.4, 16.199999999999999, 11.699999999999999, 5.7000000000000002, -15.9, -9.0999999999999996, -2.0, 2.1000000000000001, 5.4000000000000004, 8.8000000000000007, -21.600000000000001, 3.1000000000000001, 10.800000000000001, -3.2999999999999998, 11.800000000000001, 0.69999999999999996, -6.7999999999999998, -13.300000000000001, -6.9000000000000004, -0.10000000000000001, 7.7999999999999998, 8.6999999999999993, 1.0, -9.0999999999999996, -4.0, -10.5, 8.4000000000000004, -1.8999999999999999, -6.2999999999999998, 3.2000000000000002, 0.10000000000000001, -0.40000000000000002, 0.5, 4.5999999999999996, -0.5, 4.4000000000000004, 1.8, -7.9000000000000004, -0.69999999999999996, -0.59999999999999998, 2.1000000000000001, -4.2000000000000002, 2.3999999999999999, -2.7999999999999998, -1.8, -1.2, -3.6000000000000001, -8.6999999999999993, 3.1000000000000001, -1.5, -0.10000000000000001, -2.2999999999999998, 2.0, 2.0, -0.69999999999999996, -0.80000000000000004, -1.1000000000000001, 0.59999999999999998, 0.80000000000000004, -0.69999999999999996, -0.20000000000000001, 0.20000000000000001, -2.2000000000000002, 1.7, -1.3999999999999999, -0.20000000000000001, -2.5, 0.40000000000000002, -2.0, 3.5, -2.3999999999999999, -1.8999999999999999, -0.20000000000000001, -1.1000000000000001, 0.40000000000000002, 0.40000000000000002, 1.2, 1.8999999999999999, -0.80000000000000004, -2.2000000000000002, 0.90000000000000002, 0.29999999999999999, 0.10000000000000001, 0.69999999999999996, 0.5, -0.10000000000000001, -0.29999999999999999, 0.29999999999999999, -0.40000000000000002, 0.20000000000000001, 0.20000000000000001, -0.90000000000000002, -0.90000000000000002, -0.10000000000000001, 0.0, 0.69999999999999996, 0.0, -0.90000000000000002, -0.90000000000000002, 0.40000000000000002, 0.40000000000000002, 0.5, 1.6000000000000001, -0.5, -0.5, 1.0, -1.2, -0.20000000000000001, -0.10000000000000001, 0.80000000000000004, 0.40000000000000002, -0.10000000000000001, -0.10000000000000001, 0.29999999999999999, 0.40000000000000002, 0.10000000000000001, 0.5, 0.5, -0.29999999999999999, -0.40000000000000002, -0.40000000000000002, -0.29999999999999999, -0.80000000000000004], [10.300000000000001, 18.100000000000001, -26.600000000000001, -8.6999999999999993, -3.2999999999999998, -27.399999999999999, 2.1000000000000001, -14.1, 3.3999999999999999, -5.5, 8.1999999999999993, -0.69999999999999996, -0.40000000000000002, -10.1, 1.8, -0.69999999999999996, 0.20000000000000001, -1.3, -9.0999999999999996, 5.2999999999999998, 4.0999999999999996, 2.8999999999999999, -4.2999999999999998, -5.2000000000000002, -0.20000000000000001, 0.5, 0.59999999999999998, -1.3, 1.7, -0.10000000000000001, -1.2, 1.3999999999999999, 3.3999999999999999, 3.8999999999999999, 0.0, -0.29999999999999999, -0.10000000000000001, 0.0, -0.69999999999999996, -2.1000000000000001, 2.1000000000000001, -0.69999999999999996, -1.2, 0.20000000000000001, 0.29999999999999999, 0.90000000000000002, 1.6000000000000001, 1.0, 0.29999999999999999, -0.20000000000000001, 0.80000000000000004, -0.5, 0.40000000000000002, 1.3, -0.20000000000000001, 0.10000000000000001, -0.29999999999999999, -0.59999999999999998, -0.59999999999999998, -0.80000000000000004, 0.10000000000000001, 0.20000000000000001, -0.20000000000000001, 0.20000000000000001, 0.0, -0.29999999999999999, -0.59999999999999998, 0.29999999999999999, 0.5, 0.10000000000000001, -0.20000000000000001, 0.5, 0.40000000000000002, -0.20000000000000001, 0.10000000000000001, -0.29999999999999999, -0.40000000000000002, 0.29999999999999999, 0.29999999999999999, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    return models,coeffs

def get_cals3k():
    models=[-1000,-990,-980,-970,-960,-950,-940,-930,-920,-910,-900,-890,-880,-870,-860,-850,-840,-830,-820,-810,-800,-790,-780,-770,-760,-750,-740,-730,-720,-710,-700,-690,-680,-670,-660,-650,-640,-630,-620,-610,-600,-590,-580,-570,-560,-550,-540,-530,-520,-510,-500,-490,-480,-470,-460,-450,-440,-430,-420,-410,-400,-390,-380,-370,-360,-350,-340,-330,-320,-310,-300,-290,-280,-270,-260,-250,-240,-230,-220,-210,-200,-190,-180,-170,-160,-150,-140,-130,-120,-110,-100,-90,-80,-70,-60,-50,-40,-30,-20,-10,0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,310,320,330,340,350,360,370,380,390,400,410,420,430,440,450,460,470,480,490,500,510,520,530,540,550,560,570,580,590,600,610,620,630,640,650,660,670,680,690,700,710,720,730,740,750,760,770,780,790,800,810,820,830,840,850,860,870,880,890,900,910,920,930,940,950,960,970,980,990,1000,1010,1020,1030,1040,1050,1060,1070,1080,1090,1100,1110,1120,1130,1140,1150,1160,1170,1180,1190,1200,1210,1220,1230,1240,1250,1260,1270,1280,1290,1300,1310,1320,1330,1340,1350,1360,1370,1380,1390,1400,1410,1420,1430,1440,1450,1460,1470,1480,1490,1500,1510,1520,1530,1540,1550,1560,1570,1580,1590,1600,1610,1620,1630,1640,1650,1660,1670,1680,1690,1700,1710,1720,1730,1740,1750,1760,1770,1780,1790,1800,1810,1820,1830,1840,1850,1860,1870,1880,1890,1900,1910,1920,1930,1940]
    coeffs=numpy.array([[-33719.7383551,-263.748312707,-3182.51718048,-1429.82706058,-3025.5410826,213.155259437,2266.51141514,-360.234747256,-671.705672116,886.732039779,282.550399141,-672.340989688,-42.6562230009,-247.983163026,422.2624706,-352.989728466,-331.563134383,277.189968788,-930.510984722,-283.079111451,-124.458379384,-25.1987098669,243.399219266,-469.960044888,83.9046787025,94.6715625921,-62.8508455388,144.441607761,109.019363939,123.352707625,-180.138957665,-166.700991413,-13.4952584064,-209.212926401,268.465603334,-9.36433934422,27.4859163563,22.4897582198,12.7530025413,-15.3127311921,-45.8468405068,-75.3470129602,-91.9902117593,-3.90610128725,-68.9993902167,45.2482498001,-28.9350241055,-13.1915386411,2.15443667308,2.96670887781,1.33708714223,5.25984505842,-6.45194299119,-3.65250488186,-18.518252081,-1.50357286527,-29.6880521677,-30.8677610054,-2.22560178608,-12.0304104859,16.4293362981,3.959353332,9.81307259746,0.508496867888,0.892754815706,-5.04951318522,2.99223608283,1.18984898779,5.16126810248,-2.72424959905,-2.93166650903,-4.6895192021,-8.61616974617,6.11196767069,-3.40147084135,8.10463399849,-3.3960587882,-2.34016514915,-3.43653173898,-1.47884778825,-0.180750062376,-0.889317945872,0.257315221392,-0.218618402042,-0.080963047642,-0.541180388083,-0.455133175674,-0.640012340672,-1.60805464047,-0.809998928739,-0.270099275862,-0.951157574199,0.586727659478,-0.598526256261,-0.355648720842,-0.0982498984115,-1.04050581859,0.281614504234,-0.739380507402,-0.0753312870462,0.00901542800022,-0.13583818432,-0.057921066754,-0.13648361368,0.0257340571037,0.0475545012495,0.256384164088,-0.152571742257,-0.140122389204,0.0264797936968,0.210413134183,0.836796357888,0.611626383014,0.0881276528425,-0.0940766001223,-0.714844630893,-0.468516903706,-0.258791646165,-0.0968510440335,0.180331918475],[-33756.7513162,-311.420517835,-3168.86618334,-1398.81092723,-2996.25760606,217.986142726,2248.77402862,-349.046118036,-708.717080295,864.716570088,266.816460025,-659.647470949,-35.3490663284,-258.069134251,433.96159791,-348.830237479,-335.934908548,278.552553628,-928.25548469,-281.198178007,-118.834149016,-28.7068983192,244.612282973,-479.55021698,80.5766226198,94.832415576,-65.4204448668,144.876403323,107.526656022,126.36750355,-183.97524265,-167.160489281,-17.8233688152,-211.410995491,270.496961013,-8.84103785339,27.1972685776,23.8293348731,12.0244373335,-15.4492759722,-45.5440450629,-76.9257006352,-92.8360445566,-4.82403386593,-69.9045222465,45.5909688344,-28.5648018715,-13.4340272034,2.09010060562,3.14450652311,1.15517498125,5.24512682358,-6.71122714653,-3.42608985004,-18.8257610212,-1.46254527216,-29.9276529522,-31.1191437024,-2.04398363683,-12.0839719283,16.5113589645,3.8981908616,9.7610349045,0.52501213189,0.929334441485,-4.99223864906,2.92601397671,1.18069071665,5.20054491556,-2.7791771296,-2.90650586508,-4.80950113379,-8.72822692063,6.16092295255,-3.41852148473,8.16409299511,-3.42462934817,-2.39720312491,-3.44926630865,-1.47954187682,-0.168306431463,-0.884189242024,0.263210454257,-0.192409853939,-0.0519482970408,-0.550675054444,-0.462953104104,-0.634780380518,-1.64758667521,-0.825840174108,-0.269874333587,-0.966038503783,0.593363342008,-0.607336671734,-0.386188948994,-0.101765376474,-1.03771681031,0.283515470714,-0.73765951108,-0.0821921560254,0.00947750698842,-0.135602751928,-0.0540077085324,-0.137775899909,0.0269569791912,0.0447475552833,0.267383673518,-0.160680420479,-0.139573911834,0.0224770497515,0.20561007453,0.842796278027,0.608509410013,0.0839125121203,-0.101107058238,-0.720369893332,-0.471588868236,-0.260040331141,-0.0969735539762,0.182813841209],[-33793.0523859,-360.562883659,-3153.20103421,-1363.869828,-2965.17082847,222.114904916,2231.49552355,-336.25415117,-744.932164099,840.826857343,252.400644375,-646.961325772,-28.057742808,-268.37542123,447.591140188,-344.017742483,-340.821874012,279.984937128,-925.76819666,-278.770345194,-113.042633124,-31.8402342273,246.069128075,-489.957061855,77.3936595337,94.9868473946,-68.2905889353,145.57045991,106.148220499,129.626926908,-187.815725738,-167.710565869,-22.2795418317,-213.863656728,272.775402155,-8.24179673401,26.8888564019,25.1430441712,11.2833296269,-15.5820549198,-45.2905310853,-78.5226499154,-93.7500299576,-5.78045711036,-70.8702645247,45.9495906276,-28.1983364903,-13.7167550425,2.03689585678,3.31789827079,0.951921910372,5.22002039487,-6.99993099512,-3.20459332979,-19.128771058,-1.42219095115,-30.1796441771,-31.3872191653,-1.87263288767,-12.1339387178,16.5964682254,3.84345471906,9.71743963838,0.546137981842,0.966911392869,-4.93894904149,2.85673130741,1.16537472522,5.24332367622,-2.82871856203,-2.88250892183,-4.93001639247,-8.84572735942,6.21145884395,-3.43624660987,8.22515283762,-3.45577959481,-2.45823762157,-3.46394133044,-1.48280346513,-0.154599203981,-0.878800516559,0.269796909563,-0.165897593076,-0.0234457247429,-0.560129366262,-0.469626664186,-0.630303822353,-1.68771596918,-0.84196378321,-0.271730319286,-0.980940542738,0.597851544964,-0.61621887913,-0.418318972156,-0.104423922618,-1.03563695428,0.285759101182,-0.737061816188,-0.0891102329962,0.010271839232,-0.134983829204,-0.049855085683,-0.139625332511,0.0286219688263,0.0418713255582,0.279160162664,-0.168738241147,-0.138775268205,0.0180005973893,0.200965679858,0.84883320881,0.605809498429,0.0793704332232,-0.108240994648,-0.72626829338,-0.475179030718,-0.261450715116,-0.0972719789519,0.185629788885],[-33827.8260149,-411.041889541,-3134.5784429,-1325.4443414,-2931.96828094,225.680990752,2214.28450645,-322.16247157,-780.143058822,815.060050115,239.576597944,-634.382817728,-20.8030233217,-279.012097951,462.985017169,-338.595559814,-346.112013657,281.415229144,-923.11183766,-275.783662772,-107.1523454,-34.6158097957,247.743452655,-501.129105178,74.35724799,95.1484380914,-71.4750256563,146.522123184,104.892176532,133.126298704,-191.635095096,-168.351552343,-26.8616872428,-216.566408243,275.285499279,-7.56952483173,26.5640741673,26.4206929568,10.5373092338,-15.702493793,-45.0925828899,-80.1303527703,-94.7343621895,-6.77652120778,-71.8940577099,46.3159889128,-27.8340791916,-14.0369775496,1.99290967238,3.4849795542,0.727748394206,5.18644836023,-7.3196567653,-2.98842308918,-19.4261678751,-1.38316389815,-30.445622318,-31.6705553583,-1.71577581357,-12.1792362724,16.6855220374,3.79634810577,9.68300185941,0.57173269784,1.00504425509,-4.88940980956,2.78524522694,1.1434894787,5.28959020587,-2.87291484859,-2.85994751925,-5.05130669969,-8.96882238158,6.26287702592,-3.45416396313,8.28799186547,-3.48887801616,-2.52279041821,-3.48061304831,-1.48884772068,-0.139625549083,-0.87328409807,0.277313057853,-0.139113553989,0.00430602738694,-0.569340708968,-0.475253366397,-0.626727136272,-1.72844248658,-0.858511713064,-0.275856439105,-0.995745734084,0.600074734371,-0.625026175213,-0.451886140145,-0.106161627437,-1.03424454006,0.288362847461,-0.737574352726,-0.0960511057336,0.011344818048,-0.133899988811,-0.0455053235623,-0.142036324959,0.0307565716806,0.0388642334457,0.291742636179,-0.176778812295,-0.137733010911,0.0130589750389,0.196506735221,0.85488202306,0.603584056693,0.074556225877,-0.115418231676,-0.732497085193,-0.479278325551,-0.262994487971,-0.0977764223595,0.188774116897],[-33859.7291554,-462.844483371,-3111.63976126,-1284.4479122,-2896.36177555,228.463716987,2196.75299475,-307.280166839,-814.078078638,787.391640287,228.598839492,-621.997537164,-13.6252424963,-289.991553046,479.956246396,-332.631988269,-351.666948485,282.767074677,-920.364621619,-272.251583533,-101.226035176,-37.0703400308,249.596414954,-512.972057664,71.4660282882,95.3323032807,-74.9720974345,147.717065203,103.757387541,136.860705278,-195.408228516,-169.069912206,-31.5610582114,-219.5078486,278.009119192,-6.82809684623,26.2279878561,27.6529940096,9.7934762176,-15.797851856,-44.9568239686,-81.7397908141,-95.7883452869,-7.81128995524,-72.9718120621,46.6847494229,-27.4703536846,-14.3893044596,1.95566841483,3.64347175267,0.484083375252,5.14631186388,-7.67138447826,-2.7785946729,-19.7165099608,-1.34581492589,-30.7264223701,-31.9663078919,-1.57670784878,-12.218687992,16.7793272528,3.75747313998,9.65786808439,0.601641948261,1.043302905,-4.84341468489,2.712548439,1.11495988455,5.33887241221,-2.91174949324,-2.83902681272,-5.17349200143,-9.09733658231,6.31457487461,-3.47166713003,8.3529046838,-3.5233066519,-2.59018594931,-3.49936800238,-1.49783425573,-0.123406129966,-0.867778812274,0.285953017553,-0.112094978299,0.0310783042354,-0.578113429163,-0.479927657978,-0.624247458184,-1.76971739911,-0.875596864911,-0.282393465593,-1.01032191468,0.599937914144,-0.633671637985,-0.486719976258,-0.107022587697,-1.03347960049,0.291317047743,-0.73916149587,-0.102974142838,0.0126313268842,-0.132285538972,-0.0409955329335,-0.145001762839,0.033368576396,0.0356622459267,0.305143159462,-0.184839198376,-0.136445858864,0.00766257817911,0.19225378654,0.860896594579,0.601850780996,0.0695394863854,-0.122596387493,-0.738984994799,-0.483859950754,-0.264642577362,-0.098509206966,0.192222788776],[-33887.8547111,-515.961968415,-3082.75692975,-1242.12438839,-2858.24389721,230.337929569,2178.8474946,-292.189791404,-846.448773695,757.876584794,219.685444994,-609.819358726,-6.53585102718,-301.337521027,498.26884986,-326.209704545,-357.336154067,283.976628419,-917.622695998,-268.234395404,-95.315369363,-39.2652389345,251.592823157,-525.362778234,68.7203422312,95.5579277219,-78.7725630968,149.133907819,102.739800571,140.823945061,-199.111295732,-169.840978672,-36.3634272468,-222.672200469,280.927188883,-6.02261394544,25.8853068969,28.8322111734,9.05792494142,-15.8536174786,-44.8892851178,-83.3402708476,-96.9092405597,-8.88150095025,-74.0975918734,47.0506321748,-27.1053697008,-14.766995171,1.92217532122,3.79073568521,0.222860651128,5.1014793073,-8.05514989148,-2.57686037003,-19.9981590517,-1.30962438897,-31.0226491173,-32.2701279453,-1.45809897282,-12.2507854566,16.8791210414,3.72752511861,9.64180327012,0.635563566542,1.08132804937,-4.80085169743,2.63965803462,1.08001744639,5.39052579277,-2.9451083395,-2.81995230931,-5.29645655247,-9.23084588151,6.36616245804,-3.48791196072,8.42030576376,-3.55838458994,-2.65971108538,-3.52045663257,-1.50983771856,-0.105974895176,-0.862438265885,0.295909294799,-0.08490295532,0.0567148055929,-0.586330615362,-0.483765715816,-0.623098357162,-1.81145668339,-0.89327057601,-0.291417707284,-1.02451089265,0.597325549185,-0.642084631594,-0.522644395809,-0.107105053201,-1.03321161783,0.294647310074,-0.741774270799,-0.109847038034,0.0140602675086,-0.130090524932,-0.036366812914,-0.148511453563,0.0364561907228,0.0322056090058,0.319361338607,-0.192949966158,-0.134902722441,0.00181621188893,0.188229630813,0.866822586222,0.600609076757,0.0644189717351,-0.129745368834,-0.74562681492,-0.488882188967,-0.266354443749,-0.0994945678597,0.195944138333],[-33912.0518388,-569.486738071,-3047.95458352,-1199.50682107,-2817.73193939,231.315276385,2160.59541747,-277.438189801,-877.025527532,726.697363539,212.974364176,-597.811454469,0.414379658706,-313.057409133,517.539974011,-319.410558873,-362.932980687,285.00983167,-914.970606383,-263.822056492,-89.4392783129,-41.2793302095,253.700872608,-538.154218291,66.1217080803,95.8512457314,-82.8530947906,150.749033226,101.842719488,145.003500538,-202.726878448,-170.635900896,-41.2547991691,-226.039666207,284.01817708,-5.16246867192,25.5411956081,29.9534060226,8.33741972002,-15.8566742828,-44.8920819485,-84.9210881138,-98.0896318984,-9.98353116248,-75.2622309535,47.4089032146,-26.7364902309,-15.1624332026,1.88922179894,3.92439017665,-0.0535299965301,5.05448354979,-8.46894651901,-2.38536324328,-20.2688976043,-1.27338036017,-31.3346530047,-32.576939165,-1.36153248899,-12.2740970684,16.9861568564,3.70702208705,9.63424768188,0.672925148712,1.11859385232,-4.76158856808,2.56760944709,1.03919391806,5.44381956,-2.97282884383,-2.80290169545,-5.41998522029,-9.36861349215,6.41713318512,-3.50191531817,8.49037035749,-3.5933539239,-2.73067950783,-3.54413500617,-1.52492452301,-0.0873994797811,-0.8574618344,0.307317090974,-0.0576021290836,0.0811184982873,-0.593921881637,-0.486852330941,-0.623450487205,-1.85355353759,-0.911492525632,-0.302929400174,-1.03812487958,0.592154076335,-0.65018876039,-0.559442023009,-0.10655294816,-1.03326564099,0.298368925722,-0.745336028661,-0.116631906763,0.0155508427255,-0.127297369522,-0.0316685365081,-0.152535383616,0.0400171307672,0.0284605866805,0.334364615923,-0.201117958695,-0.133094658322,-0.00447702016474,0.184459198052,0.872583209123,0.599827634824,0.0592919616612,-0.136851867652,-0.752301833838,-0.494294375624,-0.2680913195,-0.100754095005,0.199892094918],[-33932.6818852,-620.656608221,-3008.12878384,-1157.51087967,-2774.88707437,231.144172485,2141.90954521,-263.726635353,-905.666459454,694.03450958,208.466357438,-585.845862577,7.16686140043,-325.024655824,537.328761088,-312.338148434,-368.269955771,285.841815463,-912.446008508,-259.110577283,-83.5870907007,-43.1918194918,255.873934982,-551.184424821,63.6646410476,96.2345688712,-87.1743214919,152.534321613,101.066653692,149.383810203,-206.247205276,-171.416932124,-46.2289537456,-229.585563159,287.253597256,-4.25934013569,25.2021678249,31.0151993958,7.63813272897,-15.7963866256,-44.961394376,-86.4743083834,-99.3174926679,-11.1150960161,-76.4552326144,47.7575500233,-26.3588119277,-15.5660520135,1.85413594274,4.04261098618,-0.341795854566,5.00798405075,-8.90931274817,-2.20619168545,-20.5268315974,-1.23577276381,-31.6621761087,-32.8809334178,-1.28728218538,-12.2871643108,17.100562742,3.69528049362,9.63369399563,0.712995546954,1.15440170525,-4.72540116761,2.49729635233,0.993229383668,5.49770078529,-2.99480795642,-2.7878532912,-5.5439227934,-9.50928387155,6.46660268828,-3.51261421064,8.56292224378,-3.6274855991,-2.80239591043,-3.57032330795,-1.54304815053,-0.067784540922,-0.853076359407,0.320175872282,-0.0302485195919,0.104267385801,-0.600865099708,-0.489163116681,-0.625392272776,-1.89589827918,-0.93010820449,-0.316867679649,-1.05093949692,0.584420147661,-0.657915719732,-0.596912697069,-0.105549910666,-1.03343925371,0.302425120196,-0.749742631584,-0.123283028129,0.0170068472543,-0.12392603552,-0.0269513875937,-0.157006100827,0.0440261577058,0.0244226829387,0.350071559109,-0.209331969257,-0.131009564058,-0.0112115486138,0.180978968716,0.87806783709,0.599440608726,0.0542312023892,-0.143901083641,-0.758881272641,-0.500015935258,-0.269837041122,-0.102294160371,0.20400131272],[-33950.5802981,-666.934141657,-2964.57052965,-1116.84161314,-2729.9532162,229.515441031,2122.43501273,-251.653969348,-932.283096637,659.932544154,206.099110194,-573.862743417,13.5593993913,-337.079972318,557.144975604,-305.081865021,-373.160506542,286.420084355,-910.065733858,-254.173528601,-77.7171715377,-45.0679606363,258.070480922,-564.327106695,61.339793742,96.7151109586,-91.6839698901,154.45750949,100.403931354,153.94677479,-209.675022073,-172.14817295,-51.2931395645,-233.283162926,290.602619503,-3.32539803276,24.877083335,32.0185066098,6.96529211239,-15.6653483279,-45.0908085835,-87.9946671076,-100.576571672,-12.2762452544,-77.6655193547,48.0931866041,-25.9654988358,-15.9697738068,1.81496724935,4.14444284499,-0.638240600577,4.96416559087,-9.37205465017,-2.0405258676,-20.769678175,-1.19537702499,-32.004706592,-33.1769618711,-1.23514644904,-12.288358895,17.2215445025,3.69128836147,9.63826991619,0.754987053227,1.18777361314,-4.69180879115,2.4293471441,0.94312701551,5.55073740972,-3.01107052261,-2.77451902408,-5.66821559262,-9.65106285386,6.51331767596,-3.51882093911,8.63730999022,-3.66013246176,-2.87430923651,-3.59871530531,-1.56399317938,-0.047317883025,-0.8494936423,0.334349513043,-0.0028929192775,0.126143062888,-0.607159959637,-0.490495620443,-0.628929948158,-1.93829104104,-0.948871575476,-0.333176532503,-1.06273783561,0.574195018613,-0.665136985107,-0.634869628473,-0.104212389109,-1.0335148708,0.306726920406,-0.754878027017,-0.129742042764,0.0183247472079,-0.120016561888,-0.0222736664491,-0.161824825261,0.0484245560629,0.0201179486029,0.366364806469,-0.217565112396,-0.128641248609,-0.0183681184348,0.177835834412,0.883159707106,0.599389738199,0.0492758838158,-0.150874566665,-0.765253277231,-0.505953013824,-0.271583470965,-0.104106994946,0.20821095883],[-33965.860536,-707.600617511,-2918.8261235,-1078.04449159,-2683.38772738,226.069141609,2101.56364625,-241.417060796,-956.894265113,624.33860541,205.743902773,-561.957510807,19.378002495,-349.035909859,576.543289175,-297.695380866,-377.432787402,286.672372758,-907.863154386,-249.032863759,-71.7671908028,-46.932512114,260.249859826,-577.49916957,59.1357654651,97.2777826721,-96.3203114263,156.482003983,99.8370846832,158.672241647,-213.014162253,-172.798174707,-56.4615828022,-237.09943314,294.031783466,-2.37207988641,24.5761146555,32.9660512796,6.32312419092,-15.46035144,-45.2730466566,-89.4761047848,-101.845546737,-13.4689948497,-78.8809632357,48.4083786069,-25.5511412792,-16.3671169145,1.77092537206,4.23000767401,-0.938917563559,4.92488431369,-9.85234076338,-1.88836601386,-20.9943589571,-1.1504121136,-32.362152417,-33.461136067,-1.20547525629,-12.2762694028,17.347838085,3.69453865121,9.6461658538,0.7981758473,1.21760008832,-4.65989999151,2.36426458727,0.890103149673,5.6013165594,-3.02206148586,-2.76227640964,-5.79300404438,-9.79185997895,6.55568490649,-3.51930656887,8.71256277842,-3.69066075156,-2.94586819456,-3.62889404627,-1.58743887076,-0.0262768009628,-0.846833118464,0.34960627828,0.0244735889612,0.146680679952,-0.612787495258,-0.49054616661,-0.633982987315,-1.98044181201,-0.967474223715,-0.351861427871,-1.07334232306,0.561643271675,-0.671642140777,-0.673074855958,-0.102571453282,-1.0333304242,0.311167294081,-0.760628269468,-0.135939401915,0.0194058090033,-0.115627655058,-0.0176949745128,-0.166874077336,0.0531347438935,0.0155989759707,0.383096309489,-0.225780872799,-0.125997691951,-0.0259205674855,0.175086458317,0.887757070255,0.599643956603,0.044438632262,-0.157745725838,-0.771342194878,-0.51200700956,-0.273311054984,-0.106166697146,0.212469782963],[-33978.6616949,-743.569685045,-2871.54654091,-1041.55067955,-2635.60318276,220.831984323,2078.81063146,-233.152868547,-979.60562487,587.240010237,207.212523159,-550.29801908,24.4536959454,-360.701053864,595.183988398,-290.212153429,-380.974022166,286.542893075,-905.880665919,-243.678630774,-65.6658388225,-48.8051180711,262.36749071,-590.666695048,57.0347141778,97.8934725221,-101.025711911,158.569698813,99.3421982255,163.535337287,-216.270664397,-173.338919791,-61.7482355584,-240.990130274,297.508456304,-1.41009662739,24.3086108757,33.8623867638,5.71211194387,-15.1817884422,-45.5004232063,-90.9131815784,-103.10124475,-14.696979523,-80.0888934688,48.6931704387,-25.1127134378,-16.7530791092,1.72178677716,4.30035232974,-1.23982134445,4.89131331391,-10.344550354,-1.74941942569,-21.1983452203,-1.09894494319,-32.7351842319,-33.7297720659,-1.19888811858,-12.2492064845,17.4779923912,3.70498877065,9.65573892941,0.84169858934,1.24287683793,-4.62851890965,2.30236347689,0.835476046038,5.64792804328,-3.02843801729,-2.75026891899,-5.9185981082,-9.92933975373,6.59198276883,-3.51289636779,8.78764361606,-3.71860529807,-3.01643235339,-3.6604043813,-1.61292062596,-0.00497797708595,-0.845171469835,0.365668599391,0.0519211828699,0.165884382556,-0.617770214362,-0.488937290752,-0.640420742736,-2.02206823476,-0.985543014807,-0.372981200403,-1.0825525917,0.54700589544,-0.677183592359,-0.711267650985,-0.100589598928,-1.03279896769,0.31563255311,-0.766895163125,-0.14181131002,0.0201519096548,-0.110837870523,-0.0132682340927,-0.172037894019,0.0580741435089,0.0109514863146,0.400095757032,-0.233925130873,-0.12308776663,-0.0338508818572,0.172810523857,0.891777737621,0.600197856346,0.0397229150463,-0.16447960272,-0.777092836759,-0.518079408578,-0.274982867654,-0.108432481725,0.216738128774],[-33989.6948797,-775.806536572,-2823.39454148,-1007.54442102,-2586.91498124,214.36931473,2054.05133312,-227.129188639,-1000.54607621,548.727620895,210.195315149,-539.072467714,28.6646791259,-371.903937875,612.851555798,-282.644189532,-383.737511829,286.000091554,-904.163943768,-238.104247478,-59.3189751902,-50.7086882635,264.380697802,-603.838739866,55.0183039774,98.5336368523,-105.755016867,160.687956853,98.8980663558,168.50477845,-219.452799094,-173.74720656,-67.1636765088,-244.903334733,301.00878629,-0.450647334554,24.0837580324,34.7132574187,5.12967748723,-14.8333591617,-45.7638254227,-92.30207041,-104.320145587,-15.96465181,-81.2766040586,48.9365543952,-24.6491804847,-17.1245647077,1.66754836606,4.35745279125,-1.53690584681,4.86431001299,-10.8421509269,-1.62353354068,-21.379813661,-1.03857604634,-33.1250990394,-33.9790600711,-1.2159458311,-12.2051812814,17.6106912866,3.72310949124,9.66576192094,0.884511055559,1.26279752483,-4.59642244043,2.243805262,0.780626655465,5.68944393384,-3.03076483598,-2.73748501932,-6.04527212256,-10.0611093761,6.62042967894,-3.49857566962,8.86149867786,-3.74372025561,-3.08532232629,-3.69280206081,-1.63992640286,0.0162653884782,-0.844605424604,0.38228533814,0.0795610985425,0.18387433975,-0.622205204149,-0.485243449973,-0.648063032677,-2.06293876487,-1.00262506658,-0.396611418332,-1.09014572996,0.530572326325,-0.681491294626,-0.749187386137,-0.0981485444789,-1.03191139656,0.320007780453,-0.773604852365,-0.14731110994,0.0204687266938,-0.105743787187,-0.00903647618741,-0.177212446521,0.0631612893789,0.00629326628606,0.417180833596,-0.241917767012,-0.119915132729,-0.0421467125637,0.171107221236,0.895164889342,0.601068559067,0.0351349039197,-0.171035800749,-0.782465667532,-0.524088308645,-0.276550147623,-0.110853906735,0.220994381874],[-34000.5431711,-805.335048952,-2775.40960098,-976.200432707,-2537.88585304,207.560858233,2027.11742357,-223.36271368,-1019.85373506,508.898276986,214.339940585,-528.523624545,31.9393949898,-382.569192256,629.377141045,-274.985933974,-385.714170982,285.021121432,-902.793853869,-232.332760024,-52.6500187779,-52.6516136051,266.251474193,-617.020938889,53.0784936573,99.1726489572,-110.472634577,162.800761672,98.4847220624,173.542106447,-222.562918412,-174.006036813,-72.7166333229,-248.786971422,304.509021105,0.495787611933,23.9101253148,35.5249469758,4.57141228855,-14.4205956942,-46.0545721628,-93.6401039939,-105.479769235,-17.2769875281,-82.4308529603,49.1259306366,-24.1612207048,-17.4799806703,1.6078368149,4.40419285954,-1.82617139128,4.84486726758,-11.3384296223,-1.51056964117,-21.53757601,-0.966188605983,-33.5339025475,-34.2051447706,-1.25777499195,-12.1429371078,17.7450315614,3.74974224359,9.67552718129,0.92546255567,1.27694602031,-4.56241882039,2.18882131424,0.727097967007,5.72513094861,-3.02956227461,-2.72285091113,-6.1733422904,-10.1850348753,6.63926761837,-3.47553734827,8.9332040712,-3.7657085562,-3.15191767251,-3.72573848509,-1.66808446318,0.0371544998672,-0.845238817202,0.399251839895,0.107532170673,0.200855908841,-0.626218369054,-0.47908807132,-0.656722047493,-2.10286035572,-1.01823860184,-0.422833730247,-1.09589042934,0.512641436029,-0.684290099711,-0.786577543404,-0.0950997335274,-1.03069142341,0.324215166108,-0.780665433191,-0.152405514207,0.0202642334946,-0.100453262594,-0.00503393778638,-0.182317663128,0.0683173576924,0.00175398669402,0.434175383981,-0.249655951211,-0.116475077297,-0.0507954461316,0.170079148534,0.89789017672,0.602288039703,0.0306983257646,-0.177365849782,-0.787433364141,-0.529965164358,-0.277957025489,-0.113384189364,0.225222120941],[-34013.4041525,-834.455949882,-2728.48453425,-947.711770248,-2489.48823081,201.037982682,1997.64731045,-221.631771775,-1037.55138796,467.743554164,219.377767665,-518.868793412,34.2141123729,-392.587590908,644.528685476,-267.210309111,-386.898131316,283.587570624,-901.864407396,-226.415323006,-45.6176097244,-54.6608052867,267.943980568,-630.186327383,51.214877251,99.7930350886,-115.145693325,164.86602567,98.0778843961,178.615385434,-225.601069362,-174.096940424,-78.4168692389,-252.588813327,307.978226485,1.41966967558,23.7958437017,36.303368592,4.03344000916,-13.9470874624,-46.3642029559,-94.9256153871,-106.558872347,-18.6401705953,-83.537287406,49.2508396808,-23.6501376545,-17.8171315946,1.54105402921,4.44367634967,-2.10380509131,4.8341560464,-11.8270915382,-1.40986968779,-21.6708669015,-0.878422333106,-33.9636054233,-34.4038786258,-1.32582621408,-12.0620756,17.8801695589,3.78548336749,9.68452578757,0.963340949514,1.28518348537,-4.52546254183,2.13778605784,0.676491321789,5.75447846683,-3.02515190215,-2.7052928051,-6.30311897466,-10.2992717188,6.64705212631,-3.44316967699,9.00214897712,-3.78400105856,-3.21560647752,-3.75886548156,-1.69718880204,0.0574183810774,-0.847191490401,0.416386707977,0.135955379837,0.217049373841,-0.629905325209,-0.470148047064,-0.666259134865,-2.14161179327,-1.03195907173,-0.451683951026,-1.09952939185,0.49352637299,-0.685316109521,-0.823189123619,-0.0913419436584,-1.02916419454,0.328200044214,-0.787934755756,-0.157060643178,0.0194365670645,-0.0950654624763,-0.00129110206667,-0.18730428158,0.0734625512929,-0.00254157466281,0.450914440773,-0.257024085333,-0.112753833016,-0.0597685565489,0.169818812252,0.899949309927,0.603896617854,0.0264545772414,-0.183401733575,-0.791967634088,-0.535639105607,-0.279150498198,-0.115979973527,0.229392251145],[-34029.4906866,-866.667228284,-2683.2283733,-922.649868514,-2442.62158832,195.193297908,1965.66396711,-221.405510807,-1053.58889148,425.253966352,225.164841646,-510.277542147,35.4099782743,-401.88557972,658.069005219,-259.275919139,-387.281521089,281.664412096,-901.448265894,-220.40749061,-38.1969741785,-56.7779117348,269.415436932,-643.289618754,49.4299733827,100.373776127,-119.738783142,166.838785303,97.6400684866,183.70026304,-228.566984383,-174.007217041,-84.2609354884,-256.253450886,311.386929925,2.31287943021,23.7476090582,37.0519124366,3.51303217668,-13.4163346543,-46.6851777781,-96.1558805633,-107.536915883,-20.0585381723,-84.5806299122,49.3027694983,-23.1197071656,-18.1339811141,1.4649793969,4.47883036691,-2.36629095749,4.83270246012,-12.3026310248,-1.31987833072,-21.7794354542,-0.77197893727,-34.4153348091,-34.5712766786,-1.4206124676,-11.9626577912,18.015820683,3.83139361696,9.69230140096,0.997046111777,1.28757517773,-4.48453343464,2.09111565672,0.630423395346,5.77696948962,-3.01797076322,-2.68378212511,-6.43480862629,-10.40211062,6.64301488152,-3.40104914874,9.06799201315,-3.79794597524,-3.27580647446,-3.79195166624,-1.72710751828,0.0767854296358,-0.850516745177,0.433532252358,0.164915265191,0.232635114503,-0.633319037477,-0.458216653254,-0.676552745456,-2.1789015089,-1.04342754785,-0.483084446036,-1.10081515981,0.473589461693,-0.684324080102,-0.858745927076,-0.0867916059603,-1.0273863221,0.331942619578,-0.795258345535,-0.161238408646,0.0178955555944,-0.0896646076305,0.00217025442064,-0.192131815991,0.078509481755,-0.00647915252077,0.467243837719,-0.263927139188,-0.108730598499,-0.0690152451451,0.170404153036,0.901371696432,0.605924988522,0.0224556426177,-0.189076028531,-0.796038874666,-0.541041912953,-0.280063367353,-0.118596977875,0.233474519209],[-34047.2775795,-903.545328073,-2640.26031224,-901.544874437,-2397.26476666,190.467447245,1931.81704227,-221.791373776,-1067.95886564,381.653163241,231.662723008,-502.742014823,35.512898769,-410.454102654,669.897404916,-251.177210079,-386.856418662,279.193406276,-901.557302185,-214.338659119,-30.3567557246,-58.9800848442,270.626294001,-656.263473958,47.7188430127,100.879267977,-124.218421673,168.684175851,97.1343354662,188.779323198,-231.441363134,-173.737472824,-90.2183858387,-259.728195744,314.718939513,3.16789816658,23.7661094743,37.7716601082,3.0082935111,-12.8342756982,-47.0120727321,-97.3236861316,-108.396275344,-21.5259920742,-85.5464808092,49.2776010933,-22.5765503481,-18.4305381666,1.37782599684,4.5117383511,-2.61059809036,4.83946948758,-12.7612949524,-1.23851167735,-21.863307132,-0.643740533513,-34.8876266618,-34.7045429561,-1.54068690724,-11.845858864,18.1527163876,3.88876791716,9.69899598771,1.02595070789,1.2843302938,-4.43859509588,2.04902930363,0.590258830461,5.79214279227,-3.00878939309,-2.65753830001,-6.56822750316,-10.4923055166,6.6274072914,-3.34924628273,9.13074014799,-3.80721860611,-3.33199008509,-3.82498006743,-1.75779048424,0.0950304225759,-0.855154259812,0.450600246287,0.194448059477,0.247738388883,-0.636511439627,-0.443332716214,-0.687499662284,-2.21443493373,-1.05237855532,-0.516816274852,-1.09968367048,0.453258737407,-0.681237927121,-0.892921357641,-0.0813669516105,-1.02544719405,0.335462256678,-0.802505105015,-0.164908884876,0.015595517714,-0.0843124701067,0.00534591888852,-0.196756491323,0.0833682083228,-0.00997996941456,0.483025934076,-0.27033503225,-0.104389922188,-0.0784714240044,0.171862896048,0.902238525312,0.608362638277,0.0187736031283,-0.194351359959,-0.799632220664,-0.546134628796,-0.280626246778,-0.121194178273,0.237450339101],[-34064.6854547,-945.195927725,-2600.3240404,-884.724628402,-2352.84958228,187.275084005,1896.85415329,-221.846401056,-1080.72896262,337.356453579,238.829710622,-496.159530832,34.5429543739,-418.3295192,679.987944204,-242.948917573,-385.624585735,276.114316943,-902.148564249,-208.247836069,-22.0783665116,-61.1984490522,271.537412925,-669.01772291,46.0717822116,101.270619483,-128.558282969,170.382019463,96.5284241274,193.836187274,-234.185968891,-173.298058395,-96.2370629534,-262.964334062,317.960144141,3.97817845556,23.8461902798,38.4635542966,2.51929678857,-12.208939727,-47.338821484,-98.4190299366,-109.122955115,-23.0275024375,-86.4220820069,49.174030867,-22.0284640216,-18.7081270208,1.27837409395,4.5436796864,-2.83377100441,4.85311723502,-13.2001552212,-1.16323155546,-21.9230895441,-0.490896845425,-35.3763604118,-34.801844667,-1.68326927928,-11.7138021061,18.2917716261,3.95873943346,9.7053020396,1.04975534951,1.27578187242,-4.38664136174,2.01161113509,0.557082538052,5.79990434024,-2.99856186983,-2.62592153176,-6.70272705027,-10.5691018881,6.6011936733,-3.28832793512,9.19059041537,-3.81164872768,-3.38362403582,-3.85799163885,-1.78924936426,0.112016819373,-0.860985835313,0.46756305896,0.224517707817,0.262475687283,-0.639512424411,-0.425758433329,-0.698977251609,-2.24796248481,-1.05863128821,-0.552488050357,-1.09620077483,0.433014661997,-0.676094097008,-0.925365762398,-0.0750095251209,-1.02345318792,0.338787668826,-0.809536544955,-0.168049941434,0.0125301800756,-0.0790546862231,0.00823181280825,-0.201141528688,0.0879571149246,-0.0130083527559,0.498136676347,-0.276261623313,-0.0997202735884,-0.0880436904057,0.174174573116,0.90266800971,0.61116252599,0.0154969259674,-0.199207324078,-0.802741732096,-0.550894722815,-0.280773781797,-0.123737367311,0.241301927236],[-34080.8409304,-991.363516836,-2563.45798678,-872.230892154,-2308.880038,185.861774398,1861.00478868,-220.720958037,-1091.91942564,292.858599628,246.621726477,-490.45036332,32.5724584623,-425.531282027,688.325534563,-234.628459471,-383.593434645,272.40029881,-903.1483176,-202.212221075,-13.3899373816,-63.3446229121,272.086027047,-681.420871153,44.4836480074,101.521982441,-132.735705395,171.920779889,95.7946291826,198.849439844,-236.750119342,-172.700610227,-102.253117847,-265.917626706,321.086994345,4.7386686683,23.9804486843,39.1288265228,2.04878408554,-11.5483739739,-47.6571654268,-99.4298170956,-109.706787768,-24.5433480987,-87.1968363732,48.9945803221,-21.4838806653,-18.9670308315,1.16570661027,4.57560934298,-3.03271187926,4.87295819672,-13.6161722511,-1.09149670642,-21.9599235566,-0.311377847332,-35.8753570377,-34.8619275041,-1.84447354679,-11.5697129029,18.4331611245,4.04139989598,9.71185421156,1.06821586282,1.26250320596,-4.3278474927,1.97899759604,0.531672765393,5.80056781346,-2.98817831048,-2.58837672825,-6.83724635228,-10.6321542561,6.5656987457,-3.21931840081,9.24789859613,-3.81110989465,-3.43004802816,-3.89091301561,-1.8215761561,0.127665022142,-0.867850191005,0.484407831525,0.255033219763,0.276976297481,-0.642278736635,-0.405892286322,-0.710811694742,-2.27928652152,-1.06211741064,-0.589558085232,-1.09051855373,0.413387024988,-0.669040974776,-0.955739978101,-0.0677871689684,-1.02151125872,0.34190789001,-0.816178739064,-0.170650558781,0.00871254766364,-0.0739275149973,0.0108312445094,-0.205252643354,0.0922175854536,-0.0155578091382,0.5124621554,-0.281738229731,-0.0947124826183,-0.0976227893189,0.177278703449,0.902783200694,0.614227633141,0.0127128578395,-0.203640036047,-0.805357538434,-0.555298702352,-0.280456858848,-0.126193363553,0.244988537359],[-34094.7710907,-1041.95469155,-2528.35421451,-863.863884369,-2264.89474721,186.483485522,1824.40082898,-217.655496012,-1101.49284999,248.781550606,255.058758142,-485.457148753,29.845142212,-432.010394933,694.97241107,-226.253185045,-380.783717396,268.068207328,-904.465934578,-196.289922214,-4.34683796659,-65.305581804,272.19414392,-693.315072632,42.9513179598,101.614859608,-136.728854964,173.295536595,94.9153545327,203.800824094,-239.072419152,-171.956183814,-108.190126107,-268.542780972,324.07619034,5.44543446721,24.1608358518,39.767774933,1.60056706904,-10.8612323189,-47.9573308138,-100.339821311,-110.141830743,-26.0478267014,-87.8629522522,48.7478656909,-20.9520618366,-19.2047143888,1.03969271797,4.6084248544,-3.20448003581,4.89816616079,-14.0063262116,-1.02089469161,-21.9750137256,-0.104168258823,-36.3772266838,-34.8847584765,-2.01906477729,-11.417507174,18.5772100309,4.13625439875,9.71920528087,1.08123147886,1.24529637365,-4.26157079443,1.951440254,0.514459824498,5.79470211568,-2.97853828303,-2.54455367589,-6.97039163672,-10.6815269704,6.52287310599,-3.14361013359,9.3034116419,-3.80564150145,-3.47045793142,-3.92369073647,-1.85474615825,0.141937384985,-0.875491999789,0.501130467654,0.285909523425,0.29133345876,-0.644744803218,-0.384231016392,-0.72277766254,-2.30822828662,-1.06290249821,-0.62737120402,-1.0829362846,0.394970232266,-0.660396712337,-0.983707211911,-0.0599133285924,-1.01973731219,0.344758426107,-0.822250051319,-0.172705010368,0.00418947262128,-0.0689632125608,0.0131700395656,-0.209048440578,0.0961163786501,-0.0176386285151,0.525901428856,-0.286818754608,-0.0893778501195,-0.107101386985,0.18108566596,0.902720656851,0.61742502023,0.0105030630164,-0.207675481739,-0.807475244486,-0.559332157632,-0.279636223594,-0.128532986602,0.24846202605],[-34105.8803794,-1097.0161099,-2493.47946629,-859.309247779,-2220.44293144,189.384127065,1787.23622379,-212.04998763,-1109.436543,205.850069639,264.1364224,-480.936442304,26.6993307591,-437.713031744,700.011305121,-217.86401538,-377.238294286,263.16124312,-905.991921925,-190.529946719,4.97517190447,-66.9644259387,271.778253968,-704.527984931,41.474358604,101.533843516,-140.522907202,174.509407709,93.8808960725,208.672834116,-241.082883736,-171.078408054,-113.958776742,-270.793380146,326.906781281,6.09622153059,24.3770509417,40.380416674,1.17871114434,-10.1582068571,-48.2283785082,-101.129970972,-110.425358639,-27.5100199225,-88.4140530575,48.4467852472,-20.4421259588,-19.4170716017,0.901208666331,4.64288368623,-3.34637855996,4.92788234585,-14.3678935907,-0.949266654242,-21.9695936873,0.131040583542,-36.8733081654,-34.8708646994,-2.20056227929,-11.2611388441,18.7244678095,4.2428123934,9.7280571439,1.08888109652,1.22516377521,-4.18729211631,1.9291734512,0.505483173506,5.78315637322,-2.97057260116,-2.49425277314,-7.10042381554,-10.7175275353,6.47524907534,-3.06282615793,9.35807569545,-3.79532344578,-3.50396796445,-3.95628961779,-1.88861300763,0.154869643193,-0.883575373098,0.517751770795,0.317060235953,0.305613527158,-0.646844509412,-0.361385778621,-0.734612826969,-2.33463033497,-1.06111640065,-0.665145638605,-1.07383419382,0.37838563555,-0.650573823326,-1.00891519616,-0.051671358679,-1.01822660641,0.347253330087,-0.827562948353,-0.174214645988,-0.000953310792612,-0.0641948642351,0.0152849661265,-0.212491562831,0.0996500669805,-0.0192887488679,0.538370151988,-0.291570185003,-0.0837376729544,-0.116364993891,0.185477833092,0.902628294984,0.620592564056,0.00895304387735,-0.211356749153,-0.809079645938,-0.562987376307,-0.278273427564,-0.130737271508,0.251675500584],[-34115.0107931,-1154.47854385,-2457.97228053,-858.251513235,-2175.06878967,194.43832227,1749.79142517,-203.523593778,-1115.83686098,164.685011309,273.739017916,-476.56863785,23.4421253578,-442.516141079,703.596115558,-209.510325331,-373.056881532,257.72344961,-907.575097169,-185.004604802,14.513951598,-68.191821698,270.755544314,-714.893672122,40.054166634,101.266217702,-144.11173946,175.575307592,92.6841154881,213.455103651,-242.715076917,-170.081973175,-119.46855907,-272.63083966,329.567651137,6.69151860988,24.6174620624,40.9687571073,0.787183615112,-9.45347362369,-48.4579642978,-101.783898629,-110.556878675,-28.8982700346,-88.8448152584,48.1086777125,-19.9614929545,-19.6002222373,0.752405044344,4.67984676065,-3.45583108744,4.96107027089,-14.6991281425,-0.874674599053,-21.9457003577,0.39444937634,-37.3540977164,-34.8207459593,-2.38164743481,-11.1042183892,18.8755091385,4.36000409841,9.7393854318,1.09146431341,1.20319506848,-4.10457161158,1.91224434813,0.504370265747,5.76704035094,-2.96516227402,-2.43735338595,-7.22546607643,-10.7404837671,6.42550435581,-2.97868095655,9.41303068604,-3.7804032838,-3.52966333271,-3.98855775258,-1.92306696694,0.166564059102,-0.891749957517,0.534320218459,0.348394184187,0.319926269794,-0.648529429941,-0.338020038185,-0.746034152432,-2.35841051583,-1.05689434024,-0.702055843925,-1.06360991959,0.36428297722,-0.640017190157,-1.03099747714,-0.0433324813354,-1.01704747229,0.349279103456,-0.831954719491,-0.175198981967,-0.00660776378602,-0.0596531932917,0.0172199570962,-0.215539239377,0.102835226985,-0.0205669617111,0.54980045998,-0.296068766845,-0.0778089748077,-0.125295214675,0.190323604784,0.902668931758,0.623559845973,0.00815286112544,-0.21472820924,-0.810146563416,-0.566274875583,-0.276344611404,-0.132792169056,0.254589637969],[-34124.2857811,-1212.18550056,-2422.33771453,-860.203980347,-2128.90408172,201.48889197,1712.28826813,-191.730451379,-1120.81410934,125.727945207,283.702037346,-472.137184977,20.2558415514,-446.32449492,705.784066428,-201.231784024,-368.357982495,251.797593612,-909.049892163,-179.81815061,24.2303023211,-68.9030230523,269.059683621,-724.279594959,38.6967954158,100.811302449,-147.49029334,176.508322102,91.3236066965,218.133538916,-243.921873902,-168.989838403,-124.64254983,-274.024247642,332.051754419,7.23238851969,24.8711564947,41.5360893285,0.431452645855,-8.76271244518,-48.632952593,-102.290870883,-110.537506564,-30.1875797734,-89.1490326877,47.748780185,-19.5154368954,-19.7523456619,0.595704234802,4.72038810744,-3.53060526456,4.99726186744,-14.998562149,-0.795136086925,-21.9058024702,0.685939501005,-37.8106634465,-34.7346279183,-2.55535142687,-10.9496518067,19.0308352148,4.48668996931,9.75467762506,1.08933256966,1.18038904277,-4.01310357359,1.9006731915,0.510510295919,5.74767479059,-2.96283225279,-2.37388170033,-7.34378143288,-10.750766552,6.37587854673,-2.89277956071,9.4691407144,-3.76109738194,-3.54672167306,-4.02024124164,-1.95807180067,0.177158421608,-0.899724150676,0.550877185965,0.379809988823,0.334387579025,-0.649723615334,-0.314765739738,-0.756742014553,-2.3795228865,-1.05038223001,-0.737309034947,-1.05256000254,0.353270702838,-0.629048285534,-1.04958164748,-0.0350733457076,-1.01624020348,0.350736565425,-0.835268361464,-0.175684530254,-0.0126666844942,-0.0553668987808,0.0190174248899,-0.218159637643,0.105705510771,-0.0215286744576,0.560131026449,-0.300366890968,-0.071614673888,-0.13377583403,0.195492868083,0.902990880364,0.626178046132,0.00818738219573,-0.217821652043,-0.810648252134,-0.56921900659,-0.273833847006,-0.134690378911,0.257174659502],[-34136.0578531,-1269.57543573,-2387.52727447,-864.792588325,-2082.61060164,210.652166328,1675.30391342,-176.200425505,-1124.50593222,89.3537907722,293.836492807,-467.603988905,17.263956981,-449.176292864,706.599795446,-193.056630105,-363.266688397,245.426288514,-910.256791392,-175.093828654,34.1054675341,-69.0591945728,266.63467363,-732.60304565,37.4138567667,100.17692318,-150.652125151,177.323169394,89.8001683215,222.684279217,-244.674401981,-167.836230308,-129.410445601,-274.950506958,334.352547391,7.7193362518,25.1282109008,42.0848464869,0.118266189223,-8.102793563,-48.7399305487,-102.643127103,-110.370403445,-31.3609945302,-89.3216238623,47.3745244322,-19.1102349593,-19.8740250866,0.433716730713,4.76547528538,-3.56868074521,5.0367879343,-15.2644602185,-0.708556376384,-21.8524843946,1.00466351927,-38.2354917575,-34.6133005857,-2.71548530464,-10.7995225312,19.1911102737,4.62246514085,9.7753829714,1.08276188486,1.15767421773,-3.91274206085,1.89460342724,0.523197286609,5.72656349812,-2.96391100582,-2.3040756348,-7.45384240966,-10.7488652654,6.3280766035,-2.80656805836,9.52686947927,-3.73761833997,-3.55456681647,-4.05116873546,-1.99359250226,0.186762596264,-0.907250458588,0.567477593981,0.411183946074,0.34906611297,-0.650302294083,-0.292217980907,-0.766399442175,-2.39792582656,-1.04176224116,-0.770153017863,-1.04087788521,0.345881989204,-0.617789381528,-1.06432346044,-0.0269663007908,-1.01586071175,0.351590571638,-0.83738922783,-0.175694706074,-0.0190273783403,-0.0513685215646,0.0207162955227,-0.220326664381,0.108307990144,-0.0222096746169,0.569307722952,-0.304479574577,-0.0651907743106,-0.141696493449,0.200867707868,0.903718486808,0.628329265942,0.0091167252252,-0.220661258787,-0.810567542253,-0.571841284846,-0.270714764878,-0.136424701386,0.259412229694],[-34152.8375807,-1326.91005489,-2353.28027322,-872.089737693,-2036.98384279,221.972525015,1639.44805793,-156.715698732,-1127.0058183,55.8417385891,303.93298242,-463.053077408,14.565695463,-451.141011126,706.124111849,-185.010702744,-357.917804756,238.651360635,-911.049096084,-170.956544349,44.0928944202,-68.658112377,263.391810176,-739.829210883,36.2187120761,99.3740800755,-153.588298792,178.037131541,88.1088027554,227.072586476,-244.960649154,-166.662492927,-133.715412144,-275.391676173,336.458901248,8.15374106479,25.3810069603,42.6154653441,-0.144286533209,-7.48884067593,-48.7674038191,-102.835452263,-110.062989293,-32.4083567373,-89.3607432161,46.9878238916,-18.7527429944,-19.9671697015,0.269481735083,4.81545083906,-3.56800769237,5.08039414299,-15.4953118421,-0.612793767724,-21.7883088053,1.34854244574,-38.6224715448,-34.4580995364,-2.85749503618,-10.6551606995,19.3556408039,4.76708809449,9.802207922,1.07215362165,1.13585699776,-3.80352778694,1.89423302241,0.541725351996,5.70524556579,-2.96861720792,-2.22824103748,-7.55432266559,-10.7352969594,6.28320393546,-2.72127600244,9.58623634531,-3.71012572666,-3.5528112625,-4.08101220607,-2.02958914577,0.195459429713,-0.914102720228,0.584186718118,0.442343672663,0.363961387391,-0.650062537789,-0.270895316054,-0.774656037168,-2.41358963088,-1.03125179672,-0.799912026948,-1.02870330369,0.342524996184,-0.606228342122,-1.07501129431,-0.0190131928917,-1.01602827112,0.351821491123,-0.838245155757,-0.175243630921,-0.0255856818696,-0.0476798484651,0.022354238247,-0.222010961893,0.110683472661,-0.0226355625473,0.577294345596,-0.308413187183,-0.0585828486236,-0.148946163617,0.206346809338,0.904944220642,0.629929881328,0.010951008516,-0.223244156969,-0.80991334389,-0.574137722219,-0.266961144984,-0.137972328869,0.261288809693],[-34177.4586026,-1384.2127661,-2318.1831378,-882.460912523,-1992.75227835,235.262393413,1604.99634667,-133.299566467,-1128.37357458,25.290932736,313.809776494,-458.568633004,12.2585827383,-452.159881805,704.482558896,-177.118857797,-352.461602091,231.530596619,-911.303249967,-167.508992509,54.1077781862,-67.7208922199,259.207710814,-745.954612559,35.123142347,98.4140622913,-156.290993825,178.66889712,86.2403624248,231.261777927,-244.779510472,-165.513407104,-137.522040222,-275.332268327,338.356768124,8.53787633813,25.6239981416,43.1270932719,-0.349097586122,-6.93321772549,-48.707219084,-102.866415702,-109.626986944,-33.3252238376,-89.2672071117,46.5906776492,-18.4485285575,-20.033433167,0.106039563139,4.87016193732,-3.52699771132,5.1286093738,-15.6904714208,-0.506089222454,-21.7157854216,1.71444073373,-38.966836631,-34.2708674074,-2.97883636999,-10.5176414075,19.5221758262,4.91989796774,9.83547330846,1.05805787025,1.11563698349,-3.68578091076,1.89962365791,0.565371233614,5.68514067478,-2.97710071338,-2.14666293558,-7.64410456699,-10.7107171634,6.24187153114,-2.63805727332,9.64706496139,-3.67865838821,-3.54116102073,-4.10916811363,-2.06610487802,0.203336053885,-0.920074527832,0.601045828846,0.473092617175,0.379028552294,-0.648783436311,-0.251229877731,-0.78123125171,-2.42650769361,-1.01910450457,-0.826041606253,-1.01616726071,0.343506154627,-0.594333124812,-1.08158052552,-0.0111995035497,-1.0169434305,0.351372707932,-0.837766383127,-0.174339007765,-0.0322353101458,-0.0443106009902,0.0239757431948,-0.223188158473,0.112860299608,-0.0228366138524,0.584068212938,-0.312171684472,-0.0518446110086,-0.15541802938,0.21183720974,0.906738883768,0.630924011602,0.0136550075165,-0.225536602499,-0.808732760071,-0.576089091912,-0.262562119824,-0.139297266214,0.262789740398],[-34211.8150425,-1442.49075456,-2281.11370766,-896.286575944,-1950.49510219,250.101076251,1571.99558312,-106.053164032,-1128.65235895,-2.24333232887,323.362231462,-454.195845112,10.4100249749,-452.069708784,701.758276644,-169.405513757,-347.017557322,224.142078191,-910.916496081,-164.830364132,64.0486027718,-66.3037074553,253.952592889,-750.997138,34.135012183,97.3108465802,-158.754205521,179.239442793,84.183357238,235.221770428,-244.135580534,-164.436255089,-140.812522423,-274.757394127,340.02810926,8.87418518802,25.8517334804,43.6173967248,-0.489112096455,-6.44526868941,-48.554159963,-102.736639169,-109.077315038,-34.1128388468,-89.0434096028,46.1844493516,-18.2023627067,-20.0740823491,-0.0539755038635,4.92868820966,-3.44500817914,5.18186801447,-15.8501108906,-0.387083288036,-21.6371508949,2.09841740961,-39.2654915154,-34.0539452657,-3.07873571494,-10.3878047452,19.6878430566,5.08025171347,9.87536446079,1.0411265697,1.09756919773,-3.56006857192,1.9107267926,0.593339113996,5.66748057896,-2.98948637471,-2.05962574069,-7.72235225499,-10.6760306538,6.20445115372,-2.55798502825,9.70908801577,-3.64314327645,-3.51948867399,-4.13500907452,-2.10323617594,0.210502406129,-0.924965884791,0.618073683183,0.503219149401,0.394165232218,-0.646264441362,-0.233609970186,-0.785925521248,-2.4366779374,-1.00561320697,-0.848134235526,-1.00335175727,0.349019924364,-0.582084298852,-1.08409757633,-0.00353958579227,-1.01886135865,0.350193558208,-0.835868851223,-0.172984885801,-0.0388713354615,-0.0412570162358,0.0256216222791,-0.223852241982,0.114863366406,-0.0228510339631,0.589626713343,-0.315752878137,-0.0450264718092,-0.161024280157,0.217259318564,0.90914842474,0.631271056523,0.0171542582268,-0.227498267205,-0.807100949813,-0.577668353161,-0.257513397621,-0.14036177372,0.263898222149],[-34255.6873112,-1501.49081802,-2241.66843624,-913.620840091,-1910.34271752,266.001198093,1540.18243483,-75.2985008349,-1127.83071236,-26.7105145196,332.557220633,-449.990777347,8.9700400705,-450.68337232,697.999322826,-161.912217477,-341.661167536,216.547170435,-909.784841562,-162.966592378,73.8145071928,-64.4821403219,247.522547903,-755.017853824,33.2529094935,96.0799878245,-160.968427194,179.773887992,81.9317190048,238.921496033,-243.046985836,-163.481639523,-143.589917176,-273.658139805,341.461543266,9.1645390021,26.0597488107,44.0833618598,-0.555681305643,-6.03141686664,-48.3079669786,-102.451009337,-108.431311519,-34.7767213933,-88.6931693929,45.7701477344,-18.0163909681,-20.0923539053,-0.208003548939,4.98957261484,-3.32226592891,5.24019047912,-15.9753834217,-0.254758414581,-21.5546784452,2.49590603967,-39.5163816051,-33.8101937181,-3.15772617075,-10.2660470447,19.8493437853,5.24723031268,9.92241487305,1.02223554007,1.08191112459,-3.42716967534,1.92734897773,0.624814652612,5.65327651428,-3.00576576093,-1.96754582669,-7.78859678267,-10.6322800927,6.17094892586,-2.4820772432,9.7717698131,-3.60364242471,-3.48785650544,-4.15789268351,-2.14103002553,0.217081036205,-0.928618125644,0.635256274148,0.53250665193,0.409242368156,-0.642314597063,-0.218358357434,-0.788612978766,-2.44414737388,-0.991076990831,-0.865947567638,-0.990345734998,0.359129307922,-0.569473718753,-1.08273033536,0.0039984651048,-1.02202480604,0.348230722501,-0.832479101709,-0.171187688284,-0.045388163857,-0.0385011071707,0.0273295856415,-0.223999988704,0.116710435531,-0.0227192163479,0.593983405002,-0.319174319701,-0.0381731419417,-0.165702109825,0.222534366587,0.912191522192,0.630950547159,0.0213406456808,-0.229094836443,-0.805113965742,-0.578868622452,-0.251826761383,-0.141130508586,0.26461231065],[-34307.5683529,-1559.29167474,-2199.99212722,-934.498051522,-1871.88556713,282.443073577,1509.4869316,-41.5971728344,-1125.85874571,-48.1313214091,341.437387194,-445.940064863,7.76080664358,-447.784086938,693.250857996,-154.696565666,-336.458548746,208.774634792,-907.780539437,-161.933909836,83.3412391561,-62.3511747824,239.856703074,-758.116017716,32.4706029062,94.7325261071,-162.924250856,180.301733317,79.4819714657,242.337758665,-241.547656525,-162.699984029,-145.866152356,-272.031473916,342.663616542,9.41179752977,26.2448976666,44.5209099882,-0.540802293445,-5.69592586843,-47.9733345466,-102.019495863,-107.707949013,-35.3241119987,-88.2212246035,45.3508168482,-17.8904215073,-20.0934762188,-0.353438967865,5.05113335296,-3.1596894764,5.30251424452,-16.0686959944,-0.10867007916,-21.4711255073,2.90186936787,-39.7182256141,-33.5427714032,-3.21653590494,-10.1519739261,20.0037477138,5.41981258579,9.97776845004,1.00240886719,1.06872613637,-3.2880487118,1.94911929229,0.658978465315,5.64320118659,-3.02581820191,-1.87109572517,-7.84273660336,-10.5805742961,6.14128537804,-2.4112699799,9.8345382868,-3.56051635114,-3.44643339121,-4.17731010112,-2.17943603693,0.223181838946,-0.930917860523,0.652568550377,0.560743766119,0.424114377066,-0.636780620516,-0.205702094677,-0.789290199218,-2.44903742669,-0.97580481778,-0.879399807404,-0.977249043292,0.373790684585,-0.556511197863,-1.07769857154,0.0114985421789,-1.02664194365,0.345421454398,-0.827563953168,-0.168956505904,-0.0516844879733,-0.0360090623638,0.0291404851078,-0.223628498072,0.118412169573,-0.022476873223,0.597162697787,-0.322482839881,-0.0313258973189,-0.169421149287,0.227590695476,0.915869544473,0.629961394073,0.0260895049155,-0.23030964677,-0.802873746727,-0.579719342779,-0.245521395684,-0.141576349155,0.264952395101],[-34365.7859964,-1615.26254615,-2156.81319708,-958.973355794,-1834.76382099,299.061621198,1479.97087507,-5.51940086996,-1122.57923893,-66.5976598399,350.155672089,-442.050418461,6.48199186836,-443.262567663,687.482090816,-147.792746355,-331.441158564,200.839191575,-904.798899362,-161.743581486,92.5629713011,-60.0479665868,230.935597932,-760.403345747,31.7845533332,93.2825576398,-164.613992496,180.848369488,76.8326406426,245.445753863,-239.682935627,-162.144483044,-147.657856523,-269.880757707,343.649564322,9.61874680973,26.4046039428,44.9245372989,-0.437804434217,-5.43857019315,-47.5613290814,-101.455391775,-106.928679301,-35.7652370055,-87.6327142948,44.9283214161,-17.8241832858,-20.0844194937,-0.488937832534,5.1113308886,-2.9593297753,5.36728971076,-16.1330590026,0.0507719483473,-21.3890125038,3.31060712462,-39.8710225524,-33.2547940788,-3.25631861786,-10.0450181858,20.1488406541,5.59719986412,10.042944728,0.982616468804,1.05793902608,-3.1439463668,1.97558040679,0.695097012762,5.63760120434,-3.0492341141,-1.77131907969,-7.88499336537,-10.5222111781,6.11539032836,-2.34640528532,9.89677323657,-3.5143149178,-3.39561848212,-4.19307767498,-2.21841049901,0.228926727553,-0.931818624904,0.669962920997,0.587710455776,0.438581147798,-0.629548398533,-0.195783890089,-0.788128932729,-2.45148071557,-0.960117184114,-0.888543610452,-0.964097431094,0.392823849566,-0.543222683919,-1.06929123431,0.0190424572366,-1.03289439671,0.34175251689,-0.821119877623,-0.166292588501,-0.057675022477,-0.0337352760496,0.0310852704994,-0.222775644685,0.119975064274,-0.0221561701183,0.599197666328,-0.325722420223,-0.0245220550983,-0.172183205878,0.232375035019,0.920159761621,0.628312658792,0.0312692691485,-0.231152959188,-0.800485198014,-0.580272825402,-0.238622212651,-0.141685486721,0.264947797543],[-34428.4655084,-1669.27997749,-2112.59369262,-987.04675388,-1798.81375517,315.836000988,1451.62341605,32.494104826,-1117.77209592,-82.2672959551,358.978677364,-438.35978712,4.83227199857,-437.108499686,680.654542689,-141.221524094,-326.624643667,192.751283439,-900.776995532,-162.397034365,101.412924856,-57.7046265943,220.781994001,-761.997664987,31.1939303928,91.74588676,-166.037034603,181.435356924,73.9907606651,248.222866645,-237.501344062,-161.864588665,-148.990107389,-267.221191161,344.441277842,9.78832617648,26.535958065,45.2881315302,-0.242251734754,-5.25522746274,-47.0885671834,-100.773596455,-106.117292597,-36.1117461509,-86.9342421796,44.502856936,-17.8171837489,-20.0737149568,-0.614230878547,5.16781195323,-2.72438884719,5.4325174707,-16.172409573,0.222192612715,-21.310455246,3.71658792111,-39.9761501936,-32.9495414357,-3.27919268292,-9.94497753229,20.2832188417,5.7786548535,10.1198666154,0.963789329124,1.04942101125,-2.99636659294,2.00618370632,0.732455548016,5.63663145272,-3.07531611584,-1.66958539397,-7.91580045364,-10.4587904439,6.09314887963,-2.28821153604,9.95804704014,-3.46573618841,-3.33598117721,-4.20532463063,-2.25800247099,0.234458974133,-0.931342820613,0.687407526265,0.613194622106,0.452415437474,-0.620575834736,-0.188682334785,-0.785481099028,-2.45161910395,-0.944343957554,-0.893577181399,-0.950916973615,0.415922129937,-0.529657314788,-1.05784350202,0.0267052261135,-1.04092114903,0.337262493348,-0.813185798413,-0.163203697989,-0.0632885885504,-0.031622945003,0.0331861013391,-0.221523677591,0.121404454461,-0.0217916159398,0.600131390519,-0.328924242793,-0.0177956824953,-0.174021355973,0.236850313592,0.925033173679,0.626039191565,0.0367691309797,-0.23165724336,-0.798059380112,-0.580607720856,-0.231169782547,-0.141459819539,0.264635983555],[-34493.8559143,-1720.36193214,-2067.67033944,-1018.52817794,-1764.02665986,332.82649374,1424.44814864,71.9961565368,-1111.24622586,-95.3606423516,368.182278131,-434.801608331,2.42448989099,-429.307792245,672.679369666,-134.984816146,-322.000438881,184.508085748,-895.694935693,-163.90319486,109.821109012,-55.43723158,209.468503613,-762.993353361,30.7005061395,90.1355300625,-167.201983024,182.077984228,70.9721604306,250.650838212,-235.056660699,-161.897128558,-149.897188962,-264.075892895,345.061281709,9.92216353415,26.6348974898,45.6053363085,0.0470134983791,-5.13974408126,-46.5759082241,-99.9904915517,-105.296763275,-36.375242583,-86.1306612682,44.0741752342,-17.867290473,-20.0687496585,-0.729404892731,5.21787148468,-2.45912324557,5.49556118214,-16.1909285532,0.403051532282,-21.2366512165,4.11469112441,-40.0362095923,-32.6299042954,-3.28850613458,-9.8519598018,20.4062952915,5.96325007234,10.2108787285,0.946863302653,1.04291099069,-2.84686170113,2.04013889386,0.770318585329,5.64014907751,-3.10333385618,-1.56750159584,-7.93580900882,-10.3918446393,6.07434314038,-2.23710845866,10.0181300071,-3.41545663488,-3.26810204812,-4.21434261753,-2.2982465071,0.239944160436,-0.929511282117,0.704911766884,0.636995417864,0.465347836461,-0.609944883611,-0.184425710177,-0.781822307623,-2.44962249757,-0.928765137251,-0.894830946832,-0.937731895241,0.442676187777,-0.515908694256,-1.04364683277,0.0345227363929,-1.05074740497,0.33202439922,-0.803811839878,-0.159697561775,-0.0684516114572,-0.0296045473869,0.0354583076826,-0.21997353112,0.122701444785,-0.0214223743389,0.600002702596,-0.332120453147,-0.0111859306328,-0.175001031279,0.240994196505,0.930445004226,0.623195330778,0.0425041483082,-0.231866133416,-0.795700191361,-0.580814830765,-0.2232196094,-0.140918185631,0.264057681268],[-34560.3947781,-1766.52007343,-2023.52667059,-1053.23341915,-1730.48156167,349.848255333,1398.42081094,112.658247439,-1102.94126788,-106.217160165,377.961971578,-431.257620322,-1.20459559645,-419.815327651,663.515872226,-129.071531966,-317.547509863,176.088471333,-889.58400091,-166.266276733,117.720066747,-53.3236506691,197.112385908,-763.461837193,30.3070599543,88.4574793912,-168.120883538,182.782775063,67.7934780426,252.712680057,-232.403424371,-162.267759575,-150.420160136,-260.471601716,345.532686808,10.0213657703,26.697635069,45.8701202365,0.428952047362,-5.08691629507,-46.0472735632,-99.1235386058,-104.48726886,-36.5676814282,-85.2251707021,43.6415764841,-17.9711556421,-20.075450078,-0.834218611768,5.2589581022,-2.16876501585,5.5537526369,-16.1930135061,0.590150075792,-21.1679453499,4.50000322186,-40.0549080202,-32.29855484,-3.28876054167,-9.76621187099,20.518073345,6.14985482463,10.3184336106,0.932826859306,1.03794834625,-2.69695498148,2.07654866683,0.807897455764,5.64773319723,-3.13276533133,-1.46677289115,-7.94592880923,-10.3226810778,6.05849136347,-2.19324266602,10.0768032768,-3.36414365542,-3.1925806644,-4.2204943355,-2.33908721264,0.245545541478,-0.926326444053,0.722462593751,0.658954716583,0.477053280779,-0.597812669548,-0.183009110435,-0.777685731225,-2.44566070049,-0.913589582451,-0.89276780317,-0.924552065561,0.472617384412,-0.502094431166,-1.02694491339,0.0425108372323,-1.06230997603,0.326127130906,-0.793052015583,-0.155779434498,-0.0730890186413,-0.0276128237435,0.0379017639889,-0.218229870806,0.123865325801,-0.0210956837058,0.598840128442,-0.335341320446,-0.00473945909831,-0.17521071269,0.244805158192,0.936331709683,0.619855292979,0.0483994888153,-0.23182727038,-0.793502130035,-0.580985805525,-0.214835014366,-0.140085842316,0.263258039115],[-34627.3057986,-1805.60849279,-1981.08627684,-1091.0334504,-1698.26907191,366.680521681,1373.55657929,154.215844907,-1092.86149474,-115.247603693,388.405620542,-427.629926878,-6.43332096358,-408.602300575,653.2830253,-123.447741389,-313.269138051,167.478198911,-882.515693494,-169.465532865,125.026227276,-51.4060455257,183.83956803,-763.469419158,30.016885648,86.7191646123,-168.812762468,183.548825778,64.4723403006,254.387628922,-229.589375327,-162.992957443,-150.600202058,-256.438987739,345.878685722,10.088637264,26.721612514,46.0779688372,0.899703380478,-5.09204378592,-45.5287801884,-98.1892742499,-103.707534646,-36.7017222436,-84.2221455926,43.204107093,-18.1254019664,-20.0987241171,-0.928298284576,5.28907754933,-1.85915293374,5.60491573865,-16.1831769953,0.779378335812,-21.1042851848,4.86754852574,-40.0365601319,-31.957768799,-3.28514664741,-9.68766980099,20.6186111408,6.33707760274,10.4444718175,0.922520876812,1.03404202546,-2.54816373173,2.11455634046,0.844270662107,5.65886752916,-3.16306241661,-1.36916075109,-7.94718263015,-10.2524120521,6.04481444468,-2.15662686954,10.1338826398,-3.31249800367,-3.10998923245,-4.22411769611,-2.38038912208,0.251413152186,-0.921827417334,0.740030422899,0.678984480059,0.487234734076,-0.584367863352,-0.184371766471,-0.773649831828,-2.43991241795,-0.898989075602,-0.887949822025,-0.911357959483,0.505234573766,-0.48831819075,-1.00796095277,0.0506811423901,-1.07549773479,0.319663784592,-0.780996569831,-0.151466946614,-0.0771399998102,-0.0255817442514,0.0405060836688,-0.216405418938,0.12490864859,-0.0208571594906,0.596668259023,-0.33859364163,0.00149672378783,-0.174754361847,0.248294146046,0.942611235707,0.616108524065,0.0543940826752,-0.231580057717,-0.791531852439,-0.581200992228,-0.206083281779,-0.138985452651,0.262281613094],[-34695.0850215,-1837.04956628,-1940.63192624,-1131.72912758,-1668.05585891,383.330881716,1349.96380742,196.512610299,-1081.06788792,-122.863202,399.53105285,-423.876324317,-13.4960924738,-395.716383463,642.152527031,-118.050951216,-309.187805945,158.689006974,-874.626474867,-173.474051174,131.648918581,-49.7112010159,169.780652474,-763.082610298,29.8354587848,84.9316000204,-169.3022338,184.363664719,61.0309088676,255.652140012,-226.661488298,-164.080783407,-150.481809203,-252.011644492,346.118950784,10.1257707811,26.7057788382,46.2262583991,1.45172574246,-5.15237582575,-45.0472097243,-97.2023839101,-102.975483338,-36.7912208186,-83.1267231544,42.7582659942,-18.3277069236,-20.1427360725,-1.01165125083,5.30699395317,-1.53658884318,5.64739765113,-16.1652446821,0.965625478824,-21.0451297715,5.21258490447,-39.9870574568,-31.609570887,-3.28351893188,-9.61608872994,20.7081483932,6.52373869015,10.5901927102,0.916350538521,1.03062130613,-2.40198127041,2.15345551071,0.878459455611,5.67303977213,-3.19364853902,-1.27656072184,-7.9407008771,-10.1819797467,6.03233058885,-2.12696070296,10.1891896289,-3.26118313695,-3.02096992926,-4.22566220087,-2.42194605117,0.257654113341,-0.916134346924,0.75756618155,0.697068982291,0.495614810021,-0.569856640735,-0.188371255107,-0.770288877184,-2.43252412891,-0.885100866612,-0.881017353431,-0.898104359709,0.539941154258,-0.474651881325,-0.986913622749,0.059044503161,-1.09015296505,0.312762188997,-0.767784801639,-0.146779104763,-0.0805735451124,-0.0234641910485,0.0432417508233,-0.214625650984,0.125864551777,-0.020732599132,0.593507511413,-0.341840073659,0.00746484479741,-0.173759302323,0.251495527179,0.949183649685,0.612066020967,0.0604395375929,-0.231150830154,-0.789831747073,-0.581519473691,-0.197028692984,-0.137639679263,0.261168277039],[-34765.3887432,-1861.53130332,-1902.62235932,-1175.03522115,-1641.08440058,400.046813507,1327.64525493,239.515996382,-1067.65474054,-129.546036184,411.347484655,-420.017158552,-22.5784706495,-381.255814237,630.245816584,-112.803503053,-305.330149992,149.73000706,-866.095817019,-178.269871834,137.516240247,-48.2613510097,155.075191129,-762.368725802,29.7733936374,83.1039956295,-169.618136449,185.205720656,57.4950345781,256.48339645,-223.668772414,-165.534799625,-150.115905662,-247.224876435,346.268584762,10.1338957075,26.6506887062,46.3122448747,2.0750598966,-5.26612568064,-44.6289497811,-96.1774400279,-102.306872798,-36.8512268468,-81.942717104,42.2971319693,-18.575822372,-20.2125782756,-1.08457826296,5.31220749618,-1.20757923893,5.67979763933,-16.142412648,1.14347899053,-20.9894721617,5.53110428546,-39.9134184896,-31.2555008134,-3.29042051321,-9.55113566552,20.7868359377,6.70885349887,10.7565414101,0.91438491946,1.02705798868,-2.25979336113,2.19263405075,0.909596207203,5.68969681646,-3.22392032143,-1.19082503259,-7.92773799983,-10.1120967939,6.01974125869,-2.10356638057,10.2423772154,-3.21076395151,-2.92619310536,-4.22563389525,-2.46361012875,0.264314507635,-0.909425705209,0.775018348167,0.713222279585,0.501911271313,-0.554539498622,-0.194761906576,-0.768137984873,-2.42360011915,-0.871997203176,-0.872680126536,-0.884684130494,0.576096056741,-0.461107863275,-0.963986715859,0.0676453744357,-1.10609123963,0.30557649994,-0.753578123001,-0.141728089551,-0.0833848714722,-0.0212240685684,0.0460606434756,-0.213022133546,0.126770500411,-0.0207252661645,0.58937392541,-0.345009205507,0.0131058309745,-0.172360286154,0.254474206607,0.955935546717,0.607863512939,0.0665002393551,-0.230551365195,-0.788432737402,-0.581987244928,-0.187732881349,-0.136070314875,0.259951388446],[-34839.3883403,-1880.15793242,-1867.34165091,-1220.61296059,-1618.77985102,416.952627716,1306.13062937,283.173820235,-1052.65034516,-135.800885193,423.903594457,-416.110855027,-33.7836838755,-365.236063287,617.618715959,-107.631491567,-301.697844037,140.598864505,-857.108813147,-183.812647876,142.579789589,-47.0656988099,139.84930334,-761.389183905,29.8437115608,81.2521995413,-169.793078197,186.051505286,53.8936953461,256.872587956,-220.657586638,-167.349796817,-149.56630851,-242.118625529,346.336519354,10.1150052992,26.5596286364,46.332429002,2.76027225609,-5.42915715519,-44.2982112048,-95.1285883334,-101.715728862,-36.8991350309,-80.6741179104,41.8141370152,-18.865908791,-20.3131209912,-1.14813344622,5.3046399224,-0.878436021296,5.70125468669,-16.1183466612,1.30767877541,-20.9361329542,5.8202654554,-39.8234131673,-30.8968448911,-3.31285118269,-9.49263689121,20.8543643463,6.89103768423,10.944256655,0.916485885419,1.02274869314,-2.1229838057,2.23161388148,0.936938111462,5.70819343029,-3.2530790929,-1.11355014849,-7.90974345604,-10.043453637,6.00549604947,-2.08547743438,10.2932816097,-3.16159764044,-2.82619456549,-4.2244270598,-2.50542489151,0.271383415399,-0.901986693817,0.792354354303,0.727451937566,0.505863887042,-0.53865655389,-0.203212506119,-0.767717138163,-2.41323081727,-0.859737593567,-0.863685263626,-0.870927249905,0.613080532203,-0.447663967267,-0.939331832118,0.0765102237823,-1.12310780835,0.298240652319,-0.738534003832,-0.136330659849,-0.0856063597986,-0.0188236292027,0.0489056245863,-0.211731093881,0.127652173259,-0.0208256533363,0.584299819878,-0.348001272151,0.0183744455454,-0.170684773364,0.257315832115,0.962769161621,0.603655649558,0.0725700013685,-0.229777250044,-0.787353550652,-0.582642443015,-0.178270326207,-0.134298948328,0.258648522069],[-34916.4730897,-1893.28043465,-1834.92033669,-1267.84042661,-1601.99442102,434.204709738,1284.87981303,327.271462427,-1036.0437273,-141.914324241,437.334582136,-412.113268123,-47.0878235862,-347.598440065,604.277171107,-102.486662087,-298.240934858,131.296034314,-847.796019784,-190.025704193,146.826939872,-46.1186695032,124.228110898,-760.189762528,30.0529666268,79.395108361,-169.862167636,186.883218113,50.2624838683,256.826166323,-217.665351,-169.506870636,-148.899583644,-236.733854961,346.326562936,10.0711788353,26.4350126702,46.2815678733,3.49914307162,-5.63538627108,-44.0745605275,-94.067500362,-101.213515214,-36.9523041328,-79.3257080268,41.3047731513,-19.1927831866,-20.4465971774,-1.20374397969,5.28395086714,-0.555458827747,5.7109068648,-16.0971695181,1.45324197315,-20.88393788,6.07801924502,-39.7245627221,-30.5346765268,-3.35663746575,-9.4404445388,20.9109176469,7.06854661707,11.1538359464,0.92245097442,1.01711832592,-1.99284575018,2.26982678047,0.959717017406,5.72764660712,-3.28030783599,-1.04615552657,-7.88829038321,-9.97673176709,5.98816671464,-2.07157994018,10.3421719085,-3.11389946442,-2.72125083784,-4.22237406257,-2.54745490472,0.278823740689,-0.894122118636,0.809575450162,0.739731948624,0.507240731174,-0.522474270478,-0.213395633274,-0.769526925869,-2.40153215321,-0.848396105434,-0.854698792415,-0.856627471289,0.650431095154,-0.434288872936,-0.913023171399,0.0855969770945,-1.14094945192,0.290849541165,-0.722800103955,-0.130612542218,-0.0872845967111,-0.0162118720225,0.0517182780759,-0.210873606793,0.128514412304,-0.0210218903945,0.578321820179,-0.350717610454,0.0232342558598,-0.168853612403,0.260113038298,0.969620203505,0.599585395624,0.0786849954699,-0.228835832579,-0.78658588077,-0.58351920929,-0.168723351632,-0.132353555458,0.257261127115],[-34994.4904008,-1900.07432137,-1804.52975579,-1315.91198727,-1590.77340884,452.286195737,1263.6936721,371.671818377,-1017.90910502,-147.914199401,451.852417012,-407.827509499,-62.3211384319,-328.295313038,590.200820234,-97.3586143565,-294.874605815,121.832940478,-838.24163819,-196.805345744,150.263038562,-45.4011847008,108.334262594,-758.769950687,30.3990181059,77.5460778314,-169.865269874,187.684078904,46.6416502082,256.360459573,-214.715646023,-171.975791064,-148.168642622,-231.110487051,346.236509132,10.0038507742,26.2747769126,46.1517181798,4.28271319888,-5.87868967505,-43.9722359756,-93.0016700018,-100.807728334,-37.0248576326,-77.9025716083,40.766598123,-19.5514634929,-20.6115836332,-1.25267607062,5.24903178455,-0.245037813624,5.70755770036,-16.0829705707,1.5753820473,-20.8316930638,6.30296521612,-39.6235552343,-30.169728302,-3.42583316742,-9.39441610728,20.9576530988,7.23959176601,11.3852039483,0.932095406546,1.00968047064,-1.87047537265,2.30657437198,0.977017307082,5.74694123918,-3.30507250928,-0.989857157215,-7.86489973038,-9.91251572792,5.96673635032,-2.06071078678,10.3897321493,-3.06773942458,-2.61143815198,-4.21985231487,-2.58973294529,0.286598432151,-0.886040078255,0.826718268529,0.750008855569,0.505817593159,-0.506289698344,-0.22507948236,-0.774002784035,-2.38864712156,-0.838052350197,-0.846235988052,-0.841561613464,0.687860113786,-0.420954134617,-0.885036939157,0.0947581347753,-1.15932914819,0.283482060442,-0.706517575219,-0.124604227706,-0.088455640899,-0.0133279328675,0.054444128053,-0.210546628727,0.12935410175,-0.0213097101426,0.571471694517,-0.353078658239,0.0276555677895,-0.166977790911,0.262957734598,0.976447403852,0.595767300813,0.0849195199643,-0.227759089205,-0.786087682129,-0.584639641519,-0.159170191469,-0.130269067303,0.255773024868],[-35070.9044395,-1900.645267,-1774.85907555,-1364.32427752,-1584.60367513,471.81025154,1242.55589828,416.129921075,-998.390016856,-153.639213026,467.66302968,-403.132599659,-79.1994280521,-307.360869717,575.38239191,-92.2626535936,-291.498437796,112.246878366,-828.534681695,-204.033361604,152.893868023,-44.9310011879,92.2718846424,-757.124704827,30.871098558,75.7178343364,-169.840960688,188.435206906,43.0658576577,255.488970457,-211.825091682,-174.719691639,-147.413082285,-225.278800902,346.060853463,9.91430875941,26.0752254733,45.933574222,5.10127469465,-6.15200207059,-44.0027800745,-91.9344402134,-100.502613507,-37.1307044521,-76.41049374,40.1959715268,-19.9383425556,-20.805041393,-1.29602938813,5.19791304008,0.0467919492029,5.69019837103,-16.0790867657,1.66905828504,-20.7779908451,6.49392213104,-39.5268605049,-29.8019599851,-3.52326445114,-9.35331087657,20.9958487979,7.40318877173,11.6374344134,0.945221519299,0.999889687612,-1.75682302581,2.34118071697,0.987916773807,5.76469009347,-3.32696715259,-0.945565321263,-7.84091325775,-9.85113621159,5.94041633286,-2.05153937137,10.4366238793,-3.02304344154,-2.49670325924,-4.21728496708,-2.63214122538,0.294697192581,-0.877890161429,0.843796138385,0.758211771741,0.501385928991,-0.490423314099,-0.238060734041,-0.781515168858,-2.37467407309,-0.828770129349,-0.838691396842,-0.825419336114,0.725170844834,-0.40754522602,-0.855331951783,0.103819447517,-1.17797848138,0.276211380328,-0.689830532743,-0.118327698051,-0.0891483507524,-0.010116141501,0.0570193829214,-0.21083121205,0.130158378824,-0.021693130654,0.563772417518,-0.355004827673,0.0316188338429,-0.165151356833,0.265959156713,0.983211854367,0.59230580936,0.0913573549498,-0.226587457922,-0.785777322245,-0.586001326711,-0.149659536013,-0.128074813722,0.254163241879],[-35143.8260036,-1896.60793768,-1744.6769907,-1412.65785157,-1582.69215929,493.157362987,1221.25777176,460.023129243,-977.57088864,-158.95418015,484.882837739,-398.037420463,-97.425425061,-284.836076987,559.806007634,-87.2236796028,-288.026129528,102.598369521,-818.765779084,-211.609605843,154.717321214,-44.7830696372,76.1227298414,-755.250050138,31.4533680531,73.9263872811,-169.825493305,189.114165756,39.556512553,254.216334277,-209.004771471,-177.693260015,-146.665872424,-219.256900935,345.786600109,9.80566472146,25.8323415051,45.6187537561,5.94368584943,-6.44622123303,-44.1751499825,-90.8684662436,-100.299086344,-37.2856240831,-74.8546747991,39.5886763936,-20.3494458709,-21.0226247969,-1.33493470219,5.1281573346,0.31488913286,5.65858473882,-16.0882822459,1.72923235334,-20.7215941725,6.64965770797,-39.4401083447,-29.4297117678,-3.65088654588,-9.3148471031,21.0259394123,7.55840421004,11.9090227238,0.961615394589,0.987268009237,-1.65266694571,2.3729965919,0.991524708884,5.77936540871,-3.34551437731,-0.913791022606,-7.81750278015,-9.79257914975,5.9082025594,-2.04268540662,10.4832646017,-2.97955540663,-2.37669926246,-4.21489097206,-2.67444552582,0.303162878867,-0.869802223754,0.860794220131,0.764266484541,0.493791177415,-0.475131942575,-0.252112071182,-0.792397474786,-2.35971441538,-0.820583129547,-0.832401519294,-0.80777068732,0.76223497119,-0.393853856026,-0.8238586583,0.112588509315,-1.19663996385,0.269059769271,-0.672840438205,-0.111800994953,-0.0893950767414,-0.00651906743194,0.0593783769223,-0.21180091139,0.130909846058,-0.0221904624508,0.555233090101,-0.356410742521,0.0351185180717,-0.163453775803,0.269233690495,0.989850286047,0.589286562562,0.0980868792234,-0.225355403836,-0.785529852283,-0.587575433828,-0.14021992212,-0.125788577499,0.252397524985],[-35211.5499693,-1889.21080633,-1713.12257019,-1460.18154709,-1584.10700742,516.452835661,1199.34509002,502.458591226,-955.458733237,-163.814553523,503.549902765,-392.552003192,-116.736646458,-260.762032561,543.442709147,-82.2748854509,-284.390041155,92.9521162193,-809.027549149,-219.456498839,155.733154747,-45.0529792267,59.9667086216,-753.137798205,32.1247471035,72.1884139437,-169.849971027,189.698329322,36.130062776,252.548792825,-206.265011643,-180.844285436,-145.962273171,-213.059089401,345.4007218,9.68143281404,25.5425924674,45.2025087888,6.79754201461,-6.75114198781,-44.4963571075,-89.8078841195,-100.19477848,-37.5041391926,-73.2385491923,38.9430374733,-20.7787224257,-21.2603656613,-1.37067153275,5.03744548732,0.554899026819,5.61271642378,-16.1131820972,1.75127988477,-20.661295,6.76967008011,-39.3680258232,-29.0498894978,-3.81007627146,-9.2763104383,21.0477062723,7.70391305432,12.1983027207,0.981092334205,0.971377583551,-1.55861519631,2.40136315791,0.98701835359,5.78942329087,-3.3601305799,-0.894789694973,-7.79565014176,-9.73648790677,5.86907843997,-2.03263305628,10.5299507951,-2.93690747907,-2.25095574469,-4.2126695455,-2.71637595278,0.312077274563,-0.861910000032,0.877673895988,0.768138946449,0.482937909631,-0.460642901506,-0.266963679331,-0.806973387933,-2.34387429083,-0.813465941455,-0.827693170707,-0.788160277577,0.798950204958,-0.379667257704,-0.790551509375,0.120903416868,-1.21501815344,0.262020172614,-0.655620479343,-0.105047946936,-0.0892318585548,-0.00248359688675,0.0614661186768,-0.213522177225,0.131594028776,-0.0228316884864,0.545852008328,-0.357221148294,0.0381531170907,-0.161959415338,0.272895145868,0.996293982886,0.586797932049,0.105210631466,-0.22407964983,-0.785192762836,-0.589325939297,-0.130879511996,-0.123423081474,0.250440428758],[-35272.4871351,-1878.77731363,-1679.31289617,-1505.82933293,-1587.81218053,541.743225522,1176.28075253,542.27481336,-932.083304854,-168.21608349,523.608275188,-386.669186018,-136.898894554,-235.224589761,526.292515812,-77.4714824634,-280.570914758,83.3866609595,-799.426919333,-227.525127495,155.936538214,-45.8311699994,43.8930929051,-750.770937913,32.8601016113,70.5220928682,-169.945709854,190.167751406,32.8051086252,250.497609084,-203.611289007,-184.118034618,-145.329536841,-206.700239709,344.895179319,9.54583129995,25.202206063,44.6859248997,7.64832870163,-7.0570998867,-44.9714000966,-88.7576631054,-100.185480916,-37.79571938,-71.5643069833,38.2605843104,-21.2182337531,-21.5154860386,-1.40411809532,4.92397958724,0.763569524718,5.55284817737,-16.1557148209,1.73082401193,-20.5962459808,6.85453381082,-39.3141927073,-28.6585543349,-4.00181797603,-9.23471953778,21.0604638388,7.83817002129,12.503684552,1.0034470761,0.951980499126,-1.47512952395,2.42567610742,0.973712410848,5.79356270702,-3.37016819159,-0.888604412554,-7.77605229334,-9.6822215591,5.82226318517,-2.01986659772,10.5769000024,-2.89476501608,-2.11907796413,-4.21051535397,-2.75762262239,0.321559095465,-0.85435552064,0.894393891719,0.769862233338,0.468861292236,-0.447220175094,-0.282331155393,-0.825535718952,-2.32731684623,-0.807308780159,-0.824873687431,-0.766162325755,0.835183187996,-0.364834440121,-0.755343334819,0.128641372053,-1.23278393737,0.255086420937,-0.638241348275,-0.0981139872606,-0.0886930924169,0.00201834745388,0.0632442808616,-0.216055937955,0.132214682535,-0.0236518636114,0.535618079392,-0.357375962282,0.0407276172541,-0.160740812128,0.277053406877,1.0024818052,0.584933406128,0.112845071027,-0.222755601465,-0.784600620387,-0.591216288388,-0.121670787923,-0.120994114664,0.248265886892],[-35324.9681767,-1864.62372473,-1643.28141321,-1548.51925175,-1592.51255912,569.10107248,1151.75604715,578.362654711,-907.577080525,-172.144505414,544.895812882,-380.424281569,-157.699565767,-208.41566915,508.461503247,-72.8944128365,-276.596808183,73.9975265094,-790.082412406,-235.787244596,155.346090632,-47.1803738523,28.0222425424,-748.128901807,33.6342151084,68.9471769761,-170.138371461,190.505041454,29.6025386505,248.076872503,-201.038336575,-187.461154311,-144.775947877,-200.196499818,344.272907988,9.40400905519,24.8081238405,44.0766530539,8.47943038559,-7.35580206169,-45.6031326308,-87.7230625657,-100.264283224,-38.1646152415,-69.8331099813,37.5444405984,-21.6599348899,-21.787159655,-1.43571807502,4.78700133694,0.939136682608,5.479714199,-16.2167903044,1.66368972159,-20.5261227139,6.90581940663,-39.2809483622,-28.2515333444,-4.22598181102,-9.18699656951,21.0638559329,7.95978924695,12.8239162146,1.0283760273,0.929164593387,-1.4025400129,2.44552654133,0.951240301202,5.79066907695,-3.3750194291,-0.895106409509,-7.75917976248,-9.62904176418,5.76728874456,-2.00309222434,10.624214734,-2.85302112204,-1.98085845574,-4.20838703717,-2.79781153634,0.331710872709,-0.847305292796,0.910891381929,0.769563122959,0.451753456491,-0.435176522451,-0.297953503126,-0.848334628184,-2.3102910283,-0.801941250267,-0.824210343923,-0.741409755983,0.870801734122,-0.349260460005,-0.718161208846,0.135746474927,-1.2495863092,0.248279502328,-0.620787887752,-0.0910741191038,-0.0878245651453,0.00697431598145,0.064698119558,-0.219451892307,0.132789550614,-0.0246831397201,0.524510148198,-0.356831874233,0.0428466734632,-0.159872551022,0.28179839522,1.00836584904,0.583773878389,0.121111381747,-0.221371553604,-0.783582607156,-0.59321843996,-0.112621080795,-0.118524225971,0.245863109221],[-35367.7391042,-1846.40355848,-1606.04189104,-1587.54714894,-1596.90247555,598.584756078,1126.05363486,610.163133618,-882.238707833,-175.694565728,567.171717901,-373.953176705,-178.991443713,-180.677510727,490.154960607,-68.6365942354,-272.530834334,64.8712063305,-781.117445716,-244.222309482,154.019431805,-49.1406036146,12.5217697746,-745.193985152,34.42477959,67.4756151177,-170.436953433,190.688454202,26.5392982941,245.303605607,-198.533436317,-190.822987021,-144.285256738,-193.566008479,343.546263426,9.26169082553,24.3581964551,43.3868769756,9.27371085618,-7.64097321294,-46.3911691286,-86.7084065275,-100.41926135,-38.6115780848,-68.0454100396,36.7962149887,-22.0978337065,-22.0759428345,-1.46501535938,4.62661836977,1.08128329517,5.39411091229,-16.2961032129,1.5465810626,-20.450852248,6.92546187569,-39.2691472267,-27.8249684844,-4.48075359396,-9.12980151895,21.0586013088,8.06809271917,13.1578637996,1.05556106366,0.903229803299,-1.34097601867,2.46068073691,0.919472412902,5.77956921423,-3.3743810793,-0.914075499888,-7.74529097709,-9.576080404,5.70412693137,-1.98137786378,10.6717725987,-2.81185881079,-1.83635293595,-4.20637664555,-2.83640943624,0.342569750057,-0.840847563231,0.92703826826,0.767420302912,0.431853410994,-0.424866484741,-0.313624081971,-0.875565829534,-2.29307020427,-0.797198181126,-0.8258566575,-0.713621379637,0.905739821279,-0.332842521513,-0.678890976341,0.142268469954,-1.26506903847,0.241688181135,-0.603387193298,-0.0840114114428,-0.0866768082207,0.0123393250823,0.0658316294689,-0.223728598089,0.133324437189,-0.0259517968863,0.512476564554,-0.355579902819,0.0444987268002,-0.159415983643,0.287183670295,1.01391342922,0.583367590931,0.130118861083,-0.219920673798,-0.781965008517,-0.595305121246,-0.103741399393,-0.11604006842,0.243238808485],[-35400.3776577,-1825.69520354,-1568.65957173,-1622.86805226,-1600.23132683,629.955463225,1099.57126513,637.539164858,-856.468557927,-179.085190617,590.213337893,-367.472906527,-200.61592809,-152.380133715,471.571691199,-64.8074539865,-268.455943361,56.0878759803,-772.651815446,-252.820871332,152.033134595,-51.7460792627,-2.42484927038,-741.935825658,35.2135296082,66.1166315664,-170.831597352,190.688779987,23.6239670225,242.208171612,-196.075254612,-194.151522521,-143.824692625,-186.824698984,342.726601934,9.1265224739,23.8509737914,42.6323801747,10.0168709224,-7.90674114977,-47.330164793,-85.7159147055,-100.636501019,-39.1340951995,-66.2026367673,36.0181434492,-22.5273970421,-22.3817538803,-1.49142057711,4.44365494307,1.19118759463,5.29679563967,-16.3928431345,1.37749170532,-20.3712579525,6.91592241893,-39.278053757,-27.3755655214,-4.76286618518,-9.0601401973,21.0459803592,8.16285157477,13.5044380998,1.08469329001,0.87472277347,-1.29046761998,2.47114249979,0.878526716178,5.75906941827,-3.36812987593,-0.945120388502,-7.73448273227,-9.52268415863,5.6333899979,-1.95431869601,10.7195004587,-2.7715128739,-1.68573711631,-4.20463232797,-2.87279545974,0.354114903238,-0.83502706365,0.942640703798,0.763602070524,0.409452196163,-0.416685401946,-0.329264506413,-0.907386705592,-2.27591588825,-0.792979090389,-0.829776828136,-0.682611975235,0.940018006435,-0.31551611697,-0.637437348552,0.148280613705,-1.27890641236,0.235441403905,-0.586152916433,-0.0770184380888,-0.0853146072755,0.0180461291741,0.0666570354533,-0.228892879822,0.133796974063,-0.027479409398,0.499449130066,-0.353644306995,0.0456816069177,-0.159403875923,0.293218678552,1.01912794353,0.583716158891,0.139972177676,-0.218397260698,-0.779585886493,-0.597440418308,-0.0950368103658,-0.113574349541,0.240400159583],[-35422.7977012,-1804.856001,-1531.5332856,-1654.57220656,-1602.21215076,662.933818166,1072.57549307,660.690871058,-830.663694968,-182.548962938,613.881971865,-361.282260673,-222.397068748,-123.960858678,452.875205785,-61.5165460696,-264.448573088,47.7056440088,-764.775316673,-261.5673486,149.474572295,-54.9973960323,-16.6254319028,-738.3297117,35.9833276439,64.8796285931,-171.300399003,190.476200864,20.8667795302,238.833127,-193.635166084,-197.398489221,-143.355000481,-179.993206604,341.826621066,9.00629699524,23.2852710049,41.8314398113,10.6986532224,-8.14763351319,-48.4106868115,-84.7451397446,-100.902817482,-39.7256415326,-64.3087788642,35.21286726,-22.9440797601,-22.7056011629,-1.51470635478,4.2394971341,1.27106373382,5.18795548907,-16.5063784259,1.15597564952,-20.2887115023,6.88047403736,-39.3050147933,-26.901499568,-5.06793349252,-8.97569443657,21.027475716,8.24424416995,13.8627701146,1.11553984382,0.844290785543,-1.25092149018,2.4769867428,0.828674164852,5.72813221138,-3.35612426966,-0.987698486938,-7.72658274245,-9.46867428363,5.55625968357,-1.92203550689,10.7673501828,-2.73226188349,-1.5294053714,-4.20333308079,-2.90636988015,0.366296182541,-0.829867260644,0.957477293552,0.758245682045,0.384890241017,-0.411045438905,-0.344919720626,-0.943881300815,-2.25904484713,-0.789265089769,-0.835752980321,-0.648357531294,0.973689991035,-0.297243744693,-0.593769929909,0.153920546886,-1.29080171816,0.229695434887,-0.569183559795,-0.070195445506,-0.0838028301938,0.0240185396648,0.0671970030279,-0.234943742338,0.134158407839,-0.0292873265547,0.485370913878,-0.351084050088,0.0464093580955,-0.159833308001,0.299859347801,1.02405660964,0.584792191923,0.150766529666,-0.216791862127,-0.776313662366,-0.599596339305,-0.0865146415725,-0.111168732508,0.237366128357],[-35434.1198255,-1786.11882538,-1494.19790552,-1682.5306293,-1602.47612305,697.641175467,1045.73576333,680.294025152,-805.25482749,-186.162309514,638.157307785,-355.553081123,-244.063539732,-95.9302070176,434.26590507,-58.8723327444,-260.55178021,39.7760844343,-757.529407614,-270.401144109,146.46201071,-58.8384266008,-29.8758551697,-734.356960278,36.7101952363,63.7691416498,-171.813907359,190.03083641,18.2858746921,235.23892705,-191.17344745,-200.523542615,-142.827374745,-173.099921743,340.865268548,8.9068501789,22.6594604339,41.0037735067,11.3119149191,-8.35945387105,-49.6184734635,-83.7905121242,-101.207075,-40.3723001263,-62.3721466454,34.3843240194,-23.3443088553,-23.0487562345,-1.53460643109,4.01581392127,1.32326521448,5.06696359553,-16.6360381901,0.883406967756,-20.2040337767,6.82241623244,-39.3454841125,-26.4031699312,-5.38998692217,-8.87470349212,21.005518031,8.31313183096,14.2318375864,1.14795225682,0.812500490474,-1.22202535039,2.47817397194,0.770211885712,5.68592287494,-3.33834949399,-1.04124615761,-7.72094007873,-9.41435598781,5.47480240661,-1.88495607002,10.8153861545,-2.69451792988,-1.36811032349,-4.20280632856,-2.93647060652,0.37905624736,-0.825321439161,0.971302131421,0.751484530562,0.358525095907,-0.408406028107,-0.360693677776,-0.985019207036,-2.24255759041,-0.786124428628,-0.843372923068,-0.611020760417,1.00683199864,-0.278043602625,-0.547955111062,0.159387519082,-1.30048866166,0.2246501063,-0.552607635206,-0.0636441998002,-0.0821922009369,0.0301672068191,0.0674743267547,-0.241860401389,0.134341557558,-0.0313968383022,0.470219040433,-0.34798396602,0.0466966425315,-0.160662982336,0.307024815358,1.0287885506,0.586552655601,0.1625684768,-0.215102898345,-0.772053855767,-0.60175320987,-0.078180719471,-0.108874280927,0.234176492254],[-35434.5125591,-1770.76946987,-1455.86115864,-1706.67033714,-1600.49726566,734.462189916,1020.28310118,697.501758752,-780.778142904,-189.915395874,663.077988642,-350.180083716,-265.317442346,-68.7914392869,415.965708307,-56.9579129912,-256.790463422,32.3503432591,-750.897282748,-279.234252019,143.144949052,-63.1617869899,-41.9645199171,-729.990562837,37.371954078,62.7823422162,-172.342305316,189.346044159,15.9014808601,231.508259751,-188.641930037,-203.493182302,-142.186300693,-166.180334834,339.863668993,8.83314424148,21.9715435399,40.1696559586,11.8508266183,-8.5410469018,-50.9337381406,-82.8431636688,-101.538793194,-41.0537631295,-60.404150568,33.5394299521,-23.7248883883,-23.410974571,-1.55057732713,3.77472564899,1.34995500885,4.93237695197,-16.7808482097,0.56256852662,-20.1174746506,6.74477655766,-39.3935125769,-25.8830909162,-5.72161553942,-8.75588737126,20.9837203314,8.37103285139,14.6102933197,1.18171350301,0.779860894877,-1.20320328109,2.47442081272,0.70342535374,5.63170577352,-3.31504789675,-1.10521150587,-7.71643626086,-9.36041302276,5.39203584894,-1.84370237868,10.8639803842,-2.65862634899,-1.20294854202,-4.20343439426,-2.96243115752,0.392314141909,-0.821262511388,0.983873854998,0.743447317603,0.3307369986,-0.409312860182,-0.376694702801,-1.03068381233,-2.22643278717,-0.783712964004,-0.852016741941,-0.570917097029,1.03960983548,-0.257978900789,-0.500124721499,0.164910079421,-1.30774403386,0.220535581503,-0.536570480498,-0.0574671350716,-0.0805243525194,0.0364012332948,0.0675087730898,-0.249594155592,0.134263969317,-0.0338222802254,0.453992043605,-0.344439155881,0.0465445062062,-0.161804774948,0.314608344533,1.03346130908,0.588948830305,0.17541302933,-0.21332675946,-0.766750110613,-0.603893361386,-0.0700401591797,-0.10675029592,0.230885403916],[-35426.1665947,-1758.71954404,-1415.31413986,-1727.0068822,-1595.82653457,773.591903512,997.768346956,713.346421888,-757.729686371,-193.76664391,688.673702133,-344.783922437,-285.973383815,-42.9695895731,398.160059041,-55.8064660223,-253.160168218,25.4673999815,-744.813048476,-287.984166231,139.682110309,-67.824905948,-52.6764386284,-725.191313211,37.9538898537,61.9151852387,-172.852629102,188.424668711,13.7353676462,227.742055425,-185.994261864,-206.267339654,-141.380065292,-159.273914982,338.838827593,8.78765388406,21.2221549728,39.3489313422,12.3112892474,-8.69161489651,-52.3317920626,-81.8926048609,-101.885506061,-41.7450744774,-58.4171407368,32.6887231406,-24.0812441084,-23.7887854123,-1.56245297525,3.51890843105,1.35320443694,4.78209868289,-16.9387995221,0.197293901996,-20.0284669703,6.65085092184,-39.4421368819,-25.3449302898,-6.0545693089,-8.61834617757,20.9663860512,8.41959469031,14.9962182246,1.2163960412,0.746736610282,-1.1938019562,2.46529167704,0.628772155031,5.56475969199,-3.2865323972,-1.1790071393,-7.71155175908,-9.30755612611,5.31163346617,-1.79888409768,10.9139039097,-2.62475855169,-1.03522873661,-4.20547980462,-2.98357477414,0.405932467318,-0.817533349228,0.994933432308,0.734244437003,0.301879871305,-0.414356474387,-0.392973897002,-1.08069410013,-2.21051392926,-0.782221624152,-0.86088872371,-0.528492052804,1.0722960014,-0.237160324777,-0.450457116302,0.170701632419,-1.31236460021,0.217578137375,-0.521217093753,-0.0517521577582,-0.0788361146216,0.0426304281805,0.067321662026,-0.258077465603,0.133829468124,-0.0365676543349,0.436694580604,-0.340548147567,0.0459340531812,-0.163124638215,0.322484385487,1.03825170685,0.591934356199,0.189308550953,-0.211451108579,-0.760383120006,-0.605988564315,-0.0621091150095,-0.104859095701,0.227552066586],[-35411.9894487,-1748.32815856,-1371.6825905,-1743.55343431,-1588.19866613,814.99210498,979.313738975,728.420613776,-736.459885596,-197.653475324,714.931051272,-338.917873077,-306.048392473,-18.8590601002,381.01521848,-55.4182148794,-249.612304265,19.1401874077,-739.189061792,-296.583948354,136.205629251,-72.6677802429,-61.8272448272,-719.936899098,38.4443849983,61.1621070846,-173.296671423,187.278582515,11.8057716325,224.03571155,-183.197875822,-208.810164415,-140.373865569,-152.419951584,337.801714798,8.76835896856,20.4167051909,38.5598643859,12.6943516654,-8.81125151299,-53.786454643,-80.9289843957,-102.233988888,-42.4187910522,-56.4237384394,31.8433390192,-24.407950221,-24.1785973295,-1.57019290292,3.25136785161,1.33541774132,4.61377341324,-17.1068646989,-0.207394459581,-19.9356384947,6.54361549869,-39.483590049,-24.7932104327,-6.38124935244,-8.46151002052,20.95683827,8.46026061104,15.3871426601,1.25152151744,0.713122399141,-1.19310486434,2.45035354375,0.547047342323,5.4845429179,-3.25316582808,-1.26200873396,-7.70444241492,-9.25637122205,5.23721543763,-1.75098767455,10.9656847122,-2.59290146246,-0.86638741259,-4.2088966317,-2.99923687946,0.419687657125,-0.81399371528,1.00419315534,0.723948445961,0.272264366785,-0.424032822111,-0.409522999896,-1.13474922712,-2.19449081976,-0.781832992336,-0.869125430763,-0.484296992138,1.10517058536,-0.215694018045,-0.399198833362,0.177030642075,-1.31419571722,0.215960593679,-0.506679120851,-0.0465634171792,-0.0771560941489,0.0487588657462,0.0669268784973,-0.26720401172,0.132930427483,-0.0396184270516,0.418338847923,-0.336414429991,0.0448316938007,-0.164447420497,0.330514631762,1.04333550321,0.595483439666,0.204208735702,-0.209438173928,-0.752974553251,-0.60800023346,-0.0544067872116,-0.103246823622,0.224240747644],[-35395.3061106,-1737.27379467,-1323.92395014,-1756.24863048,-1577.51839282,858.085665719,965.188836355,742.784779532,-717.09998353,-201.536285316,741.731869292,-332.226175737,-325.639456972,3.24203496662,364.69135658,-55.7745289408,-246.073529312,13.3664580197,-733.925546621,-304.996325731,132.795801403,-77.538483132,-69.2977902982,-714.236378351,38.8343665646,60.5271048153,-173.618907213,185.926433686,10.119508082,220.471408995,-180.232659527,-211.08790825,-139.15563833,-145.656522902,336.751418333,8.77039594983,19.5660041702,37.819626873,13.005387952,-8.90033956204,-55.2699978638,-79.9448557967,-102.572469571,-43.0503728887,-54.4384726888,31.0138698291,-24.6984914522,-24.5766120649,-1.57423439602,2.97518582958,1.29998726861,4.4256875802,-17.2815976458,-0.645564424536,-19.8375356336,6.42589695455,-39.50974926,-24.2327125353,-6.69543461213,-8.28516022867,20.9560278779,8.4938484559,15.7798359449,1.28650223226,0.678782359859,-1.20045504517,2.4292852242,0.459378909362,5.3908476176,-3.21511099274,-1.35323611517,-7.6930630244,-9.2072773965,5.17174455541,-1.70055117248,11.019406425,-2.56280995508,-0.69788399736,-4.21315838168,-3.00883985215,0.433303849711,-0.810599276687,1.01135579518,0.712578254582,0.242230353816,-0.43869154565,-0.426235933487,-1.19241147143,-2.17796741407,-0.782681792354,-0.875879110924,-0.438914795235,1.13844426409,-0.193638125193,-0.346732619777,0.184194017854,-1.31316046452,0.215778490042,-0.493041448055,-0.0419427933694,-0.0755236068302,0.0546850123371,0.0663344528056,-0.276835761896,0.13144595536,-0.0429432000951,0.398957695984,-0.332117310306,0.0432193413035,-0.165571251525,0.338559901117,1.04885544871,0.599579626419,0.220010536387,-0.207209544161,-0.744577479839,-0.609867004567,-0.0469596858503,-0.10193519785,0.221009432318],[-35379.5349159,-1725.36548375,-1271.8486726,-1765.13085376,-1564.19089768,902.092540286,955.408000007,756.482386867,-699.683343852,-205.347675188,768.879900517,-324.464077427,-344.922421579,22.9632245518,349.248166733,-56.8132130178,-242.419788151,8.13685582314,-728.922128038,-313.197404517,129.498560495,-82.3150108473,-75.0171594251,-708.123078413,39.1235235461,60.025226797,-173.762412245,184.395675627,8.67333555889,217.120029706,-177.092281384,-213.081765611,-137.72633734,-139.025691697,335.677367465,8.78644445819,18.6848366944,37.1442884367,13.2538263236,-8.96102926478,-56.7527743046,-78.9353222039,-102.891212611,-43.6210587283,-52.4775297132,30.2062253281,-24.9471273132,-24.9791086466,-1.57573832084,2.69344232724,1.25080955369,4.2177246034,-17.4590153475,-1.11019128563,-19.7323241207,6.30010378528,-39.5136041844,-23.6691271545,-6.9921328292,-8.08954585661,20.9638825529,8.52136631063,16.1702944588,1.32054013837,0.643192336573,-1.21514602253,2.40192085479,0.367239411043,5.28379032566,-3.17244404581,-1.45143480155,-7.67547501357,-9.16060545835,5.11758378582,-1.64815855173,11.0745949442,-2.53416676934,-0.531500272609,-4.21771085049,-3.01193642686,0.446484333152,-0.807432753673,1.01613910304,0.700092025889,0.212129619315,-0.458561191964,-0.442886876305,-1.25308570378,-2.16046757488,-0.784803334155,-0.880362365586,-0.392913816148,1.17218046629,-0.171026993611,-0.293546837698,0.192469460712,-1.30924170803,0.217111852075,-0.48038301865,-0.0378988139717,-0.0739965277088,0.0602969122541,0.0655248602402,-0.286822128767,0.129255183849,-0.0464779216056,0.378626651533,-0.327683502359,0.0411083733428,-0.166291044601,0.34649055156,1.05490052196,0.604189877524,0.236559728659,-0.204679741668,-0.735273449829,-0.611512839788,-0.0397981943093,-0.100941451073,0.217910586847],[-35368.0195505,-1714.51318097,-1216.65896971,-1770.38481006,-1548.89568944,946.247546732,949.952947597,769.624403523,-684.226189858,-208.897787503,796.096799904,-315.451300233,-364.124324542,39.7975881831,334.615193641,-58.4358604745,-238.483224677,3.44900530396,-724.096490456,-321.186041086,126.316909854,-86.9381495877,-78.9640642942,-701.646463292,39.3180813879,59.6782623473,-173.671563733,182.721239117,7.44862882828,214.035575516,-173.788924658,-214.793208134,-136.096685928,-132.568893476,334.561352158,8.80644991543,17.790089516,36.5483630254,13.4523713228,-9.00028474201,-58.2040721573,-77.8996106692,-103.182323319,-44.1187666245,-50.5580160121,29.4217918599,-25.1502698899,-25.3820754477,-1.57643760851,2.40912237974,1.19190302835,3.99159121033,-17.634341995,-1.59339336201,-19.6184454415,6.16791744345,-39.4902904563,-23.1088520762,-7.26745224113,-7.87526691774,20.9798042249,8.54425650295,16.5536840805,1.35252910145,0.605526262755,-1.23633662312,2.36828450631,0.272400616071,5.16388810552,-3.12541395227,-1.5551134082,-7.65000230223,-9.11647793036,5.07656801122,-1.59434085793,11.1301416472,-2.50660691404,-0.369365177021,-4.22215869379,-3.00813306697,0.458924902604,-0.804684684181,1.01827461317,0.686402106498,0.182354141499,-0.483745392711,-0.459145295103,-1.31598355782,-2.14144269593,-0.788090757448,-0.881885509601,-0.346800708193,1.20627556994,-0.147904668465,-0.240218950428,0.202065923082,-1.30247591144,0.220032289488,-0.468779639498,-0.0344052288641,-0.0726495348894,0.0654649234054,0.0644337520512,-0.296993698507,0.126257458506,-0.0501153572817,0.357462005124,-0.323080104566,0.0385458779954,-0.16641992704,0.35420724411,1.06148573796,0.609263393664,0.253644599226,-0.201775114827,-0.725158968755,-0.612850930874,-0.0329462064537,-0.100282181005,0.214986311083],[-35363.6890905,-1707.16080175,-1160.00983831,-1772.21538941,-1532.6169889,989.705863202,948.198055439,782.093648022,-670.696291265,-211.9452369,822.996343458,-305.094510247,-383.434016778,53.2826196084,320.664054708,-60.5403978904,-234.085604162,-0.685664074961,-719.400446689,-328.981811693,123.211863238,-91.3954501542,-81.1741289934,-694.880104876,39.4258583891,59.5133215523,-173.291531815,180.940515796,6.41635628032,211.254971449,-170.353524143,-216.231609848,-134.29951923,-126.325785212,333.376412285,8.81827876307,16.9008505442,36.0457950308,13.6156988181,-9.02871088054,-59.5930957898,-76.84161285,-103.440490367,-44.5376549699,-48.6985332995,28.660653067,-25.3043683138,-25.7805255176,-1.57801652787,2.12515442113,1.12759422586,3.75035757102,-17.8025877019,-2.08717952405,-19.4946966492,6.03047970219,-39.4367435642,-22.5583479253,-7.51883433261,-7.64293590305,21.0018382581,8.56363460222,16.9244942216,1.38124630623,0.564766771574,-1.2632035706,2.32853493028,0.176758324519,5.03206379507,-3.07425161422,-1.66258057116,-7.61520609303,-9.07479530979,5.0498525473,-1.53937127148,11.1844901077,-2.47959498638,-0.213676073517,-4.22599167089,-2.99705437544,0.470335479179,-0.802649654857,1.01751491467,0.6714038278,0.153327204081,-0.514247424777,-0.474583003225,-1.38017906861,-2.12033523442,-0.792324138203,-0.879872059837,-0.300985768122,1.24049113128,-0.124300944703,-0.187421967227,0.213121959667,-1.29292387711,0.224550830719,-0.458278528102,-0.0314171043332,-0.0715635059879,0.0700392717866,0.062972821414,-0.307165697363,0.122367371836,-0.0537227429739,0.335611482504,-0.318224514346,0.0356009618415,-0.165794267613,0.361646377156,1.06856601367,0.614756240621,0.271010259614,-0.198420931847,-0.714334489493,-0.613782438892,-0.0264295871393,-0.0999623363522,0.212265320698],[-35368.2008336,-1704.3661508,-1104.15722382,-1771.03922967,-1516.07170418,1031.77655407,949.454044835,793.560576547,-659.103725702,-214.213740285,849.070297625,-293.385908814,-403.107894475,62.8986698657,307.29945479,-63.0630819338,-229.06576887,-4.28926730129,-714.789061861,-336.628252203,120.141560138,-95.6827058748,-81.6858358423,-687.932980925,39.4558960124,59.5515203696,-172.574791525,179.094758305,5.54429102119,208.798735817,-166.826126434,-217.411536102,-132.3791781,-120.343024142,332.092588825,8.81000340267,16.0344924425,35.6495741356,13.7583943945,-9.05830115331,-60.890944594,-75.7699655387,-103.660866698,-44.8765745155,-46.9179601278,27.917563945,-25.404595134,-26.1712338549,-1.58158739237,1.84397800806,1.06283030753,3.49763983159,-17.9592512372,-2.58375318242,-19.3603254297,5.88904047225,-39.3508389069,-22.0234958672,-7.74515864597,-7.39248316365,21.0276733541,8.58064029391,17.2772333589,1.40570247132,0.519925619397,-1.29489609162,2.28281122757,0.0823625367885,4.8894576626,-3.01906780544,-1.77208074098,-7.56990971788,-9.0352107251,5.03781035005,-1.48320232443,11.2357166363,-2.45254369878,-0.0667246219863,-4.22869789009,-2.97838206063,0.480476765538,-0.801685424773,1.01370528017,0.654956006154,0.125509341714,-0.550004713272,-0.488745767241,-1.4447056897,-2.09667348566,-0.797145470641,-0.873888478891,-0.255749085149,1.27446747703,-0.100139860065,-0.135829518271,0.225811177916,-1.28061446666,0.230682970461,-0.44893741984,-0.028885819325,-0.0708055328153,0.0738667459168,0.0610470948929,-0.317147457267,0.117500746807,-0.0571621460751,0.313243486054,-0.313014669882,0.0323636867852,-0.16427403061,0.368765643663,1.07605450337,0.620651246777,0.288406451843,-0.194542467184,-0.702891153785,-0.614215402522,-0.0202759714042,-0.0999869390077,0.209785280678],[-35381.6716239,-1705.19960648,-1051.10898721,-1767.2376943,-1499.45741658,1071.83003137,953.09649593,803.355893279,-649.480221299,-215.328328832,873.825285357,-280.187795409,-423.470239223,68.2435855387,294.38597939,-65.965853742,-223.275991839,-7.39958536704,-710.187287152,-344.1813123,117.054732054,-99.8060088202,-80.547868157,-680.911890669,39.4153366155,59.8007470719,-171.481519297,177.227882554,4.7978334574,206.679195538,-163.252271171,-218.344254521,-130.386772679,-114.660799956,330.672171599,8.77000430202,15.2045170078,35.3697325016,13.8944497154,-9.10102768461,-62.0715987982,-74.6951309955,-103.837878623,-45.1360136683,-45.2313647105,27.1862475144,-25.4453438025,-26.5502678874,-1.58795008211,1.56727455957,1.00269046734,3.23662051108,-18.0998535541,-3.07587627433,-19.2148604647,5.74466639343,-39.2312609846,-21.5087533901,-7.94661931637,-7.12362103051,21.0547332972,8.5961415756,17.6067367854,1.42509107452,0.470002272933,-1.33042306758,2.23121670623,-0.00868997118722,4.73727900966,-2.95995686484,-1.88193624189,-7.51324312608,-8.99694926316,5.04026084891,-1.42545927098,11.281892913,-2.42470413961,0.0694855218177,-4.22968872223,-2.95185847945,0.489152795751,-0.802128630385,1.00677037912,0.636894591933,0.099348459613,-0.590850098563,-0.501183341902,-1.50861223636,-2.07004199629,-0.802107788012,-0.863665131567,-0.211255889936,1.30780378952,-0.0753274846295,-0.0860282716186,0.240257697545,-1.26555981437,0.238404179406,-0.44078534831,-0.0267492384526,-0.0704235414324,0.0768157409672,0.058560231815,-0.326746551074,0.111594522237,-0.0602942981284,0.290521902239,-0.307350546759,0.0289307612735,-0.161756065094,0.375548467149,1.08382391732,0.626950447851,0.305596271827,-0.190063563701,-0.690906744649,-0.614062412686,-0.014511419873,-0.100358567623,0.207575896449],[-35401.9032693,-1708.32314052,-1002.14747777,-1761.09938955,-1482.44903518,1109.18238112,958.876799862,810.7251435,-641.877370659,-214.673023241,896.892599456,-265.24996958,-444.747905298,69.0174168453,281.609574595,-69.2315056744,-216.566003078,-10.0358502553,-705.507507088,-351.700253361,113.858367254,-103.802439235,-77.8290461433,-673.872813843,39.3084657145,60.2607018227,-169.979685232,175.368809929,4.13763185002,204.895583603,-159.672243809,-219.03398283,-128.363063166,-109.300430303,329.06312109,8.68801956634,14.4183851073,35.2134990181,14.035188611,-9.1678670881,-63.1134212893,-73.6237204278,-103.967306063,-45.3168992782,-43.6480110954,26.4602966462,-25.4223051962,-26.9102721349,-1.59839272787,1.29602747336,0.952217837822,2.97048881903,-18.2197104657,-3.55752111255,-19.0581578804,5.5979405464,-39.0775519692,-21.0169262585,-8.12375429845,-6.83657003322,21.0804115174,8.61120330222,17.908225697,1.43861880145,0.414288299025,-1.36871192494,2.17415422195,-0.0943440945919,4.57669593032,-2.89704156282,-1.99067934708,-7.44472432959,-8.95901180237,5.05680284703,-1.36561828404,11.3212750936,-2.39500106478,0.193385601245,-4.22843666566,-2.91723014128,0.496227090616,-0.804233955285,0.99668421354,0.617097757349,0.075270172221,-0.636498544878,-0.511547803554,-1.57101867774,-2.04006666861,-0.806783918398,-0.849034106748,-0.167527167136,1.34003753254,-0.0497724733211,-0.0385426478141,0.256427659004,-1.24775564395,0.247669397659,-0.433772267857,-0.0249314725434,-0.070457266943,0.0787756158433,0.0554285827207,-0.335792748772,0.104628442551,-0.0629895480149,0.267597491825,-0.301124074892,0.0253984961466,-0.158189040703,0.38200794623,1.09169873556,0.633641628557,0.322361855623,-0.184917401513,-0.6784315011,-0.613218114305,-0.009148144947,-0.10108797762,0.205636193867],[-35426.1106314,-1712.64327725,-957.477196589,-1753.03412707,-1464.55747631,1143.44729172,966.766334408,814.963844235,-636.333593339,-211.616495899,918.060104202,-248.425367125,-467.115372632,64.9628911777,268.587724021,-72.8447923468,-208.817198883,-12.2066665803,-700.678203683,-359.253947536,110.432509817,-107.725030078,-73.6079530664,-666.840897688,39.1436998511,60.9285638792,-168.047901179,173.528177465,3.52187158463,203.424681899,-156.119949695,-219.485063756,-126.332040085,-104.268769302,327.212956773,8.55681945676,13.6808830271,35.1845650231,14.1883887681,-9.26792786431,-64.0026602935,-72.560717978,-104.047047154,-45.4200184892,-42.1716646012,25.7329329867,-25.3318437362,-27.2424067889,-1.61463461378,1.03138067048,0.915915408183,2.70253912548,-18.3142650106,-4.02438937547,-18.8909782878,5.44881298863,-38.889160985,-20.5490576022,-8.27692978657,-6.53142870095,21.1025763903,8.62720940913,18.1779768477,1.4454117769,0.352537404411,-1.40879211652,2.11233197346,-0.172681313546,4.40881463413,-2.83051225336,-2.09715988025,-7.36410183417,-8.92019337065,5.08679110107,-1.30308707141,11.3522933573,-2.36228136495,0.303915323496,-4.22452513468,-2.87428478313,0.50157007873,-0.808181982159,0.983453717708,0.595522535881,0.0536677273281,-0.686525483171,-0.51961068425,-1.6311640413,-2.00646156587,-0.81076513412,-0.829906401131,-0.124454188266,1.37068326336,-0.0233676224194,0.00622111369957,0.274209776237,-1.22718088214,0.258412353068,-0.427785206513,-0.0233645204562,-0.0709460647037,0.0796558492169,0.0515986966957,-0.344145366488,0.0966358293963,-0.0651417932007,0.24460914556,-0.294238766202,0.0218633810991,-0.153555538164,0.388172411593,1.09947395506,0.640687667991,0.338522618975,-0.17905529523,-0.66548006768,-0.611583549424,-0.0041749481063,-0.102191735725,0.20395172021],[-35452.9732454,-1717.46740374,-915.118105373,-1743.57963098,-1445.75148038,1174.64161284,976.491589616,815.652490089,-632.816620968,-205.83195978,937.186182723,-229.709780736,-490.679142441,55.9012496,254.946203606,-76.7377960013,-199.961393251,-13.9277208663,-695.671212868,-366.910888847,106.606770462,-111.62378774,-67.9934893481,-659.789918121,38.9493846823,61.8049032879,-165.679584557,171.694498661,2.90383394933,202.21591494,-152.624648246,-219.706748543,-124.304785218,-99.5646945132,325.07017996,8.3745100973,13.0003651465,35.2832241621,14.3584521612,-9.40894412633,-64.7330561657,-71.5133560676,-104.078702747,-45.4470910471,-40.8035759654,25.0001342157,-25.1703525687,-27.5355444936,-1.63873491901,0.776233046405,0.897803426422,2.43704344837,-18.3792694387,-4.47380099216,-18.714993446,5.29572054619,-38.6654956222,-20.1053083201,-8.4060367331,-6.20861223369,21.1193540326,8.64492401577,18.4131167219,1.44427390468,0.285082958645,-1.449732507,2.04692996155,-0.241868844731,4.23477918019,-2.76063663554,-2.20049785075,-7.27147320107,-8.87933462867,5.12924065858,-1.23738247217,11.3736720784,-2.32537528233,0.400523906932,-4.21748931722,-2.82289551832,0.504965946187,-0.814100795628,0.967113024396,0.572293779819,0.0349255439669,-0.740296474038,-0.525175875446,-1.68840719622,-1.96906662848,-0.813691081917,-0.80624656908,-0.0818234967771,1.39935004251,0.00401144880911,0.0479573482156,0.293387889094,-1.20380971213,0.270511351575,-0.422647324961,-0.0220023632096,-0.0719546704384,0.0793914133932,0.0470552954696,-0.351685751206,0.0877152294863,-0.0666614042294,0.221696392377,-0.286605859718,0.0184200094483,-0.147854053972,0.394075795878,1.10693093237,0.648026770278,0.353927238117,-0.172455094869,-0.652047183429,-0.609065701366,0.000423374419835,-0.103686206641,0.202485525846],[-35482.8801555,-1723.75807803,-872.504237227,-1733.50307879,-1426.73716204,1202.96876088,987.946371513,812.865249599,-631.190509496,-197.325895365,954.138039495,-209.304207969,-515.505844053,41.6439299165,240.410712959,-80.7504424227,-190.002512264,-15.2431940246,-690.535703942,-374.725429895,102.195882752,-115.526659305,-61.07987574,-652.67569248,38.7791626838,62.8886444176,-162.882547653,169.834394258,2.23315831153,201.2012316,-149.211636833,-219.710568413,-122.274954244,-95.1813546609,322.597454427,8.14456680604,12.3910903876,35.5073352489,14.5455589922,-9.59876073461,-65.3069186246,-70.4895608896,-104.064923963,-45.3999551249,-39.5429220764,24.2587964222,-24.9373174103,-27.7788367788,-1.67299145312,0.53620661577,0.901400846346,2.17887131829,-18.4108309068,-4.90421555631,-18.5323531944,5.13638464881,-38.4069421159,-19.685875847,-8.51065103461,-5.86908615384,21.1302272278,8.6654944831,18.6119930953,1.43366706227,0.212915177268,-1.49053196431,1.97976822956,-0.300138267089,4.05588542333,-2.68783469306,-2.30015583611,-7.16735933567,-8.83546635407,5.1830600264,-1.16824346827,11.384528242,-2.28330891769,0.483016599706,-4.20711610975,-2.76294813517,0.506078903232,-0.822049815518,0.947733292606,0.547777821282,0.0193759588415,-0.79699779452,-0.528068302979,-1.74222226895,-1.92780978709,-0.815277006452,-0.778157695809,-0.0394297973036,1.42571326233,0.0325207777326,0.0864963202421,0.313731742664,-1.17761707117,0.2838367341,-0.41818919912,-0.0208227108248,-0.0735731798567,0.0779327656203,0.0418265509472,-0.358324669466,0.078034466842,-0.0674673209562,0.199008944979,-0.278147019536,0.0151447743125,-0.141115903904,0.39974830326,1.11386144578,0.655611269967,0.368456501901,-0.165119127199,-0.638120018889,-0.605606664386,0.00467894164806,-0.105591548615,0.201202527485],[-35518.0777736,-1733.79187514,-827.651920036,-1723.71949423,-1408.97917159,1228.43161696,1000.73418996,806.671066858,-631.168291847,-186.383954381,968.77823965,-187.640396375,-541.674546797,22.137658782,224.712306539,-84.6557353209,-179.012928558,-16.2030416331,-685.383330047,-382.759112806,97.0207135689,-119.462349089,-52.960712272,-645.460206406,38.7072759057,64.1808725216,-159.674407313,167.896869853,1.45876815781,200.301773483,-145.906981871,-219.504254136,-120.236388754,-91.1022385874,319.766851212,7.87525232183,11.8718788644,35.8529660939,14.7462851144,-9.84424487882,-65.7333053426,-69.4985643205,-104.009375818,-45.2833993634,-38.3858466219,23.5078131516,-24.6327102804,-27.9618263284,-1.71964532244,0.31899169988,0.929901667952,1.93315858564,-18.4055690339,-5.31565422067,-18.3457721753,4.96827182992,-38.114894578,-19.2905769419,-8.59047596762,-5.51385092242,21.1348635544,8.69013281272,18.7741362107,1.41196565886,0.13763439192,-1.5303355434,1.91308149941,-0.345819933936,3.87344441774,-2.6124736916,-2.39586388392,-7.05262549189,-8.78784262941,5.24680114898,-1.0954090405,11.3842574022,-2.23511306281,0.551633348678,-4.19320925292,-2.69439039321,0.504519797169,-0.832048909551,0.925414528635,0.522493444269,0.00731178035839,-0.855705970505,-0.528138074241,-1.79220013565,-1.88270651845,-0.815318829454,-0.745896658652,0.00298335232281,1.44946876711,0.0623713274404,0.121745858063,0.33500699111,-1.14857273691,0.298210668343,-0.414205023092,-0.0198261611531,-0.0758981309551,0.0752440858813,0.0359847211971,-0.363997795273,0.0678073267048,-0.0674889550223,0.176702437848,-0.268782784087,0.0120988986519,-0.133407691558,0.405220760317,1.12005811903,0.663415934594,0.382008134951,-0.15704905267,-0.623674164683,-0.601174653335,0.00863900243819,-0.107925954145,0.200064856991],[-35561.0250741,-1748.64729065,-778.677612552,-1715.4170107,-1393.85269742,1250.94898746,1014.27110129,797.271300658,-632.504636192,-173.383777974,980.994183983,-165.126246987,-569.046925475,-2.42261804689,207.623523499,-88.2576369595,-167.139859248,-16.8676663289,-680.322217632,-391.045019077,90.9493095978,-123.424625851,-43.7479658705,-638.087720954,38.8146675708,65.6639254415,-156.087086746,165.828211409,0.532941066131,199.447075889,-142.720972404,-219.089212557,-118.178802801,-87.3025438597,316.556897249,7.58052770339,11.4579180733,36.3121667371,14.9536396957,-10.1535606836,-66.0221912705,-68.5480616791,-103.916265625,-45.1003523836,-37.3284338955,22.7496844584,-24.2569629191,-28.0745388649,-1.77939220673,0.132409382282,0.986081410339,1.70369236213,-18.3621733174,-5.70896664592,-18.1589848711,4.78952035389,-37.7908392524,-18.9195189865,-8.64492660772,-5.14482044424,21.1324814277,8.71979952291,18.8999834641,1.37796198265,0.0614435421015,-1.56844980357,1.84887629907,-0.377684269964,3.68865522438,-2.53528287975,-2.48732356416,-6.92832301875,-8.73613581743,5.31894808888,-1.01893654928,11.3725271045,-2.17983172893,0.607036001696,-4.17553764561,-2.61731543055,0.499930814947,-0.843942537668,0.900316567595,0.496942674326,-0.0010415628587,-0.915513303794,-0.525396099245,-1.83800440241,-1.83390199547,-0.81368522028,-0.709763773227,0.0455876678424,1.47037318609,0.0937321850667,0.153642929882,0.356941081887,-1.11669930316,0.313391134511,-0.410442638475,-0.0190384549203,-0.0789781249191,0.0713128752591,0.0296368265318,-0.368643812967,0.0572454214932,-0.066689013177,0.154930110967,-0.258464501174,0.00934617293698,-0.124813798463,0.410510070137,1.12533441466,0.671409841666,0.394496270526,-0.1482480133,-0.608698609966,-0.595753121513,0.012348172199,-0.110700254666,0.199025433007],[-35612.7265178,-1766.66577565,-723.260233525,-1709.81833433,-1381.8403693,1270.39329202,1028.00183004,785.111483392,-635.103451059,-158.63385233,990.669646808,-142.000225864,-597.239509791,-31.6065909077,189.102552445,-91.4337407857,-154.587927056,-17.3203545742,-675.408561951,-399.555700506,83.9088783304,-127.317922952,-33.5665864691,-630.474420743,39.1743831904,67.2932531124,-152.173342126,163.590084392,-0.579580683286,198.590336312,-139.629910936,-218.459668187,-116.076336008,-83.7592494978,312.951102528,7.27850076206,11.1551596986,36.8727582472,15.1580590445,-10.535678702,-66.1811517675,-67.6398361307,-103.788304896,-44.8474096989,-36.3693103436,21.9893015204,-23.812896671,-28.1091040384,-1.85066918267,-0.0172469674615,1.0722785838,1.49206764163,-18.2821437428,-6.08496098414,-17.9759171018,4.5996487691,-37.4351533367,-18.5739689704,-8.67342860059,-4.76562340563,21.121883071,8.75497070176,18.9907432031,1.3312360047,-0.0130131291398,-1.60418875806,1.78849838389,-0.395246123539,3.5026829864,-2.45757379513,-2.57399756913,-6.79544006763,-8.68062069362,5.39818222542,-0.939647177103,11.3494049021,-2.11675310612,0.650194506822,-4.15385354598,-2.53208278395,0.492054703095,-0.85731002257,0.872717619309,0.471519012309,-0.00555919730372,-0.97560097894,-0.520132511546,-1.87934159439,-1.78170713597,-0.810333992136,-0.670050425479,0.0882829476944,1.48830112598,0.126634950674,0.182178762496,0.379229741567,-1.08212782088,0.329111007641,-0.406666739192,-0.0185126658118,-0.0827780044519,0.0661622595011,0.0229175269731,-0.372191196295,0.0465285977184,-0.0650937146375,0.133845453678,-0.247211358533,0.00696063439879,-0.115420609064,0.415573921261,1.12955385354,0.679530112145,0.405856624246,-0.138731000152,-0.593228544727,-0.589342687656,0.0158272578572,-0.113914160808,0.198033459673],[-35673.994318,-1785.09319448,-660.85460631,-1708.37195595,-1372.82214288,1286.45082716,1041.79491918,771.001134114,-639.094503315,-142.404060267,997.617478298,-118.471601718,-625.74810485,-64.9026177425,169.348357127,-94.1048888654,-141.627097865,-17.6573442149,-670.658011686,-408.218159079,75.9015965214,-130.965656084,-22.5411386684,-622.56739023,39.8496191194,68.9984031148,-148.00476694,161.163927297,-1.90941315236,197.707481361,-136.586823554,-217.611647471,-113.890974162,-80.4516482913,308.944336171,6.98995631431,10.9618013298,37.5196587319,15.3484767992,-11.0035913512,-66.2146214414,-66.7702327771,-103.627350336,-44.5190639973,-35.5103350447,21.2283466371,-23.3080473264,-28.0622606336,-1.92929163134,-0.125049974649,1.19011340123,1.29823415373,-18.1693188592,-6.44383793875,-17.8005462291,4.39924725165,-37.0482435067,-18.2570888677,-8.67598092759,-4.38091326086,21.1017968755,8.79672544173,19.0482007181,1.27216496487,-0.0829239500888,-1.63677790767,1.73268809123,-0.398813722733,3.31684432762,-2.38130918407,-2.65517622244,-6.65490094458,-8.62221061347,5.48325606604,-0.859095162226,11.3151430731,-2.0456304575,0.68206672944,-4.12804250001,-2.43923023742,0.480770275492,-0.8714902146,0.843013097335,0.446530799049,-0.0062256242291,-1.03527600827,-0.512863541255,-1.91593958344,-1.72654038785,-0.805347535464,-0.627090613754,0.130708365841,1.50318756367,0.161060973086,0.207331722494,0.401667315475,-1.04514954091,0.34513854384,-0.40271702499,-0.0183163813132,-0.0871792831391,0.0598483984698,0.0159664252493,-0.374557077876,0.0358011421503,-0.0627850442315,0.113604713226,-0.235094541591,0.0050104324286,-0.105319992512,0.420322418861,1.13263490879,0.687697862101,0.416018619638,-0.128519590737,-0.577361964971,-0.581963829576,0.0190963833784,-0.117555155258,0.197056395484],[-35745.0228853,-1798.86335314,-591.427082897,-1712.45974585,-1365.99772115,1299.10652401,1056.05634644,756.538148816,-644.909974741,-124.887083876,1001.6273579,-94.513420933,-653.843884549,-101.704705452,148.744023306,-96.2630200491,-128.580591268,-18.0014393235,-666.030323072,-416.911357926,66.9944213935,-134.088650068,-10.8061305873,-614.299878292,40.8907891131,70.6782695503,-143.681982544,158.548794684,-3.47797442651,196.79798351,-133.513772031,-216.553107833,-111.569489493,-77.367011628,304.538690617,6.73702464498,10.8644019471,38.233069724,15.5106804084,-11.5767966456,-66.1230706274,-65.9301746743,-103.437446868,-44.1038685561,-34.7568046794,20.4683000033,-22.7535076826,-27.9340875615,-2.0084390043,-0.187854277983,1.33990519864,1.11994667523,-18.0304730006,-6.78528795693,-17.636824877,4.18946353866,-36.6296771582,-17.9742127271,-8.65245822385,-3.99709030267,21.071169287,8.84617127031,19.0747171275,1.20196042575,-0.145305124686,-1.66529926263,1.68135034719,-0.389698758704,3.13257271888,-2.30918874466,-2.73007174932,-6.50747148146,-8.56257729565,5.57336390963,-0.779571977022,11.2702974137,-1.96661516049,0.703502692088,-4.09811868051,-2.33955938407,0.466128330332,-0.885561756445,0.811769247175,0.422178625151,-0.00315502174251,-1.09403015573,-0.504388388622,-1.94752195826,-1.66894435486,-0.798915168736,-0.581163622629,0.172256900124,1.51508037768,0.196845128759,0.229078709897,0.424079977773,-1.00618496918,0.361287918542,-0.398473572362,-0.0185327919859,-0.0919710618422,0.052470981249,0.00893047666923,-0.375652018219,0.0251737355803,-0.0599113802897,0.094368646678,-0.222241799554,0.00356047224894,-0.0946024568578,0.424619233653,1.13456591749,0.695793862126,0.424917417754,-0.117652722325,-0.561262659399,-0.573651761739,0.0221590150274,-0.121605850411,0.19606816467],[-35824.8061842,-1800.02900544,-514.687163487,-1723.1706237,-1359.86340442,1308.86728217,1071.37296683,743.831962994,-653.165284905,-106.25306714,1002.60040457,-69.9134253379,-680.636099413,-141.195416162,127.798977581,-97.9792113237,-115.831614668,-18.4725956935,-661.436412073,-425.463016833,57.3387869416,-136.334607579,1.48564546693,-605.599277746,42.3297606298,72.2050493063,-139.320002642,155.759278831,-5.28986926112,195.886086936,-130.311604947,-215.302562078,-109.050003801,-74.4906628518,299.753227694,6.54153985072,10.8393861595,38.9906348751,15.6272634766,-12.2771657602,-65.9052204868,-65.106442545,-103.222790839,-43.584240979,-34.1119480417,19.7155578053,-22.1621340916,-27.7290811035,-2.07925904734,-0.204339249947,1.52079962436,0.952395510341,-17.8745858919,-7.10895614981,-17.4882343511,3.97262866963,-36.177652051,-17.7311476778,-8.60185021093,-3.62151031322,21.0289594313,8.90397790221,19.074134487,1.12262093578,-0.197156667875,-1.68892441462,1.63354276615,-0.369977669966,2.95125299326,-2.24420657303,-2.79785861107,-6.35360032633,-8.50376188419,5.66832149819,-0.703653819603,11.215951859,-1.88023515829,0.715672003094,-4.0640651871,-2.23415962197,0.448319335325,-0.898449078428,0.779638527523,0.398550391361,0.00341570300205,-1.15153479919,-0.495672546738,-1.97388357209,-1.60952553652,-0.791288206624,-0.532462500337,0.212206307223,1.52424972057,0.233668479331,0.247526358338,0.446346750972,-0.965739436894,0.3773684392,-0.393826375984,-0.0192595590019,-0.0968718185276,0.0441522050102,0.00197244555004,-0.375396063699,0.0147247808922,-0.0566612827627,0.0762703350656,-0.208821593751,0.00266224537931,-0.0833449368697,0.42831186428,1.13543519365,0.703677237743,0.432526398506,-0.106182429381,-0.545128893004,-0.564476930439,0.0250120754833,-0.126036258309,0.195047642264],[-35911.1926155,-1783.81433676,-432.300763487,-1740.89732213,-1353.22341057,1315.96654996,1087.96821425,734.048882651,-664.09268642,-86.715690243,1000.5267826,-44.7146081049,-705.500926547,-182.365254238,107.059633163,-99.2746196415,-103.74566108,-19.1388540232,-656.797467626,-433.71079836,47.1794618252,-137.444105378,14.1837195039,-596.493522282,44.1862523743,73.47341059,-135.010589247,152.823799369,-7.34061819688,195.010620037,-126.916141774,-213.870725497,-106.29180097,-71.7933555645,294.630997494,6.42014073564,10.8697741981,39.7726202541,15.6836079275,-13.1185485154,-65.561556663,-64.2894667101,-102.981158534,-42.9510580085,-33.5733860704,18.9776057747,-21.5486727569,-27.4556491519,-2.13402065575,-0.17379289499,1.73180132646,0.790233121633,-17.7088763506,-7.41477909693,-17.3574089908,3.75279027938,-35.6924471279,-17.5313698749,-8.52340179368,-3.25966487249,20.9745476329,8.97089646745,19.0516058713,1.0360584761,-0.236172593429,-1.70714956212,1.58824357761,-0.341505717651,2.77397912191,-2.18855679933,-2.8576503627,-6.19391428509,-8.44707627327,5.76783728262,-0.633323124633,11.1536902031,-1.78743546534,0.720418378196,-4.02583425997,-2.12415761535,0.427515063567,-0.909284869839,0.747159944344,0.375708067259,0.0131744476918,-1.20756426338,-0.487387505962,-1.99496346082,-1.54884987801,-0.782649601098,-0.481287671685,0.250012864858,1.53120233324,0.271252731468,0.2630143278,0.468455715107,-0.924387292827,0.393131035853,-0.388740273866,-0.0205663713385,-0.101635914096,0.0349926911702,-0.00474659772523,-0.373747130548,0.00449790744633,-0.053165032534,0.0593643351476,-0.19498223783,0.00233925563412,-0.0716373093209,0.431315085895,1.13540931933,0.711259167727,0.438877083951,-0.0941754210009,-0.529137829343,-0.554563216974,0.0276754800432,-0.130788756694,0.193994219084],[-36001.6613587,-1752.38222081,-349.647358797,-1764.82420939,-1346.22552533,1320.01819604,1105.50996541,726.88925633,-677.252862559,-66.5696740413,995.527047475,-19.3969812478,-728.472492944,-224.253596408,86.7948586447,-100.029532606,-92.5723482455,-19.9941711147,-652.095088122,-441.586581246,36.7936840073,-137.383161832,27.1820289263,-587.135522035,46.4784510596,74.4412327448,-130.806046768,149.780933199,-9.6120136941,194.212814518,-123.338006248,-212.25848952,-103.299141493,-69.2333661986,289.231793827,6.37920678986,10.9524725113,40.5652143562,15.6732821004,-14.0992814679,-65.0976200568,-63.4804912788,-102.702597452,-42.214422649,-33.1264785096,18.2580318966,-20.9272712133,-27.1265459809,-2.16916053019,-0.095642478527,1.97156512712,0.629706476742,-17.5362045322,-7.70299369476,-17.245426366,3.53565468897,-35.1787401231,-17.3734566171,-8.41817323067,-2.91361801863,20.9084048428,9.04820573862,19.0133498756,0.943577570401,-0.26117024111,-1.72005105635,1.54488024945,-0.305263906118,2.60160612446,-2.14275241357,-2.90881821401,-6.02945613714,-8.392484741,5.87122832582,-0.569124221892,11.0854230227,-1.68924816797,0.719946312474,-3.98347860329,-2.01071167949,0.403851052607,-0.917663910978,0.714681656159,0.35368558144,0.0257690795216,-1.26197307107,-0.479692140428,-2.01092700539,-1.48732843911,-0.77299485801,-0.428119338989,0.285612797198,1.53655094547,0.309499714715,0.276155460773,0.490534093201,-0.882636846276,0.408354969317,-0.383255592189,-0.0224625519275,-0.106120187042,0.025059015012,-0.01110080022,-0.370747434669,-0.00549629358601,-0.0494407027401,0.04361351575,-0.180794940513,0.00258532676854,-0.0595848733449,0.433666306762,1.13470347663,0.718555821919,0.444082783261,-0.0816953499856,-0.513400179455,-0.544087562557,0.0302002895105,-0.135793390813,0.192932808812],[-36092.6166469,-1711.06794153,-271.278670029,-1793.36192698,-1339.31265292,1320.66897816,1123.18852519,721.401478287,-691.893478446,-46.0242101538,987.900318824,5.30365497636,-749.736596675,-266.02014046,67.1075507519,-100.094584388,-82.4817232996,-20.9696873349,-647.354503453,-449.056594902,26.3969703494,-136.256539217,40.367306912,-577.729912559,49.207472793,75.1071808983,-126.748713411,146.672349379,-12.0721833681,193.524266948,-119.623759502,-210.461498206,-100.102691549,-66.7658027432,283.618892335,6.41807400414,11.0875674968,41.3561665312,15.594931112,-15.206631997,-64.5239475276,-62.6850537105,-102.378030311,-41.3960067721,-32.7517171799,17.5593167605,-20.311012468,-26.7551948044,-2.1838697023,0.0291918351925,2.23770363043,0.468339999566,-17.3577984834,-7.97465719822,-17.152556348,3.32699318235,-34.6433282565,-17.252598506,-8.28821928133,-2.58334082863,20.8313261787,9.13713135169,18.965443428,0.846313548058,-0.271688346334,-1.72815157585,1.50305645303,-0.262088186187,2.43492155214,-2.10619601602,-2.95106170215,-5.86136470938,-8.33927680763,5.9777334814,-0.510779599744,11.0134442939,-1.58667517302,0.716626864374,-3.9371069838,-1.89504003741,0.377565482951,-0.923458161554,0.682501481673,0.332461447908,0.0408371081807,-1.31468715138,-0.472519632199,-2.02213939701,-1.42529867144,-0.76225269493,-0.373479741529,0.319255502771,1.54094215265,0.348376167595,0.287666213788,0.512701018384,-0.840936867191,0.422840863162,-0.377450256821,-0.0249217231768,-0.110238389674,0.014422022518,-0.0169978420598,-0.366502999835,-0.0152674293355,-0.0454694119638,0.0289406428806,-0.166287385688,0.00338733243018,-0.0472988798511,0.435472680346,1.13356113473,0.725616135985,0.448325617091,-0.0688138702201,-0.497970187511,-0.533245053054,0.0326426874634,-0.140973874233,0.191891329524],[-36180.7417029,-1665.20485193,-198.650370506,-1825.02791458,-1332.50428966,1317.91071781,1139.94871556,716.163537488,-707.244803548,-25.1492229931,978.024061328,28.590634298,-769.438308707,-306.936904533,48.055568839,-99.3567302513,-73.6247113568,-21.9705682705,-642.631304616,-456.095632558,16.0983116063,-134.258010738,53.5671663222,-568.485463039,52.3492741151,75.4819403411,-122.892684911,143.539137983,-14.6928261835,192.955907451,-115.8397554,-208.481593097,-96.739897463,-64.3399732287,277.856533146,6.5322337794,11.2725732247,42.1310349388,15.4482743876,-16.4247477353,-63.8570482155,-61.9114068973,-102.004618898,-40.5212586699,-32.4294061816,16.8860942757,-19.7131299235,-26.3544849315,-2.17847627642,0.197698935764,2.52663052313,0.304224400181,-17.1752426767,-8.23199826644,-17.079483556,3.1312096308,-34.0939702832,-17.1622940959,-8.13590730509,-2.26789306335,20.7433444432,9.23823867437,18.9132344731,0.745426155446,-0.267851312395,-1.73214925685,1.46228446178,-0.213162143924,2.27476198168,-2.07794632893,-2.98436969492,-5.69084684908,-8.28644936876,6.08667826052,-0.457710600455,10.9402146353,-1.48084611347,0.712956415758,-3.88686466691,-1.77836011304,0.349045394595,-0.926696597935,0.650971848236,0.311944834723,0.0579817946893,-1.36564540354,-0.465741217672,-2.02909446339,-1.36310325438,-0.750361047421,-0.31786879475,0.351328700566,1.54499615897,0.38778628707,0.298246389179,0.534983573349,-0.799753117467,0.436368063879,-0.371427711629,-0.027889624518,-0.113919521758,0.0031845956246,-0.0223851381522,-0.361157552221,-0.0248229425076,-0.0412454957289,0.0152676225208,-0.151476004216,0.0047275204704,-0.0348848170617,0.436879065547,1.13222524734,0.732477733616,0.451811764758,-0.0556136807986,-0.48287898428,-0.522223679968,0.0350507812671,-0.146241921722,0.190882908486],[-36263.9881626,-1619.30961683,-131.735201239,-1858.61761176,-1325.63848033,1312.30548901,1154.6787377,709.791616371,-722.648975339,-4.00744297104,966.316819035,49.6685073387,-787.755762196,-346.424880552,29.622017469,-97.7254570737,-66.1452220206,-22.8985870272,-638.009708996,-462.674884139,5.93946786224,-131.645237816,66.5977876664,-559.601512415,55.8687472312,75.5781240176,-119.300870481,140.424645266,-17.4444227036,192.501100431,-112.070337061,-206.332617124,-93.2505373682,-61.9023622024,272.011876527,6.71478483986,11.5028315367,42.8740939073,15.2342798041,-17.7376812637,-63.1182408818,-61.1722204009,-101.582473353,-39.6175680292,-32.1372670811,16.2437512757,-19.1465305065,-25.9389829464,-2.15373826982,0.405699760966,2.83377788535,0.136246663553,-16.9903379009,-8.47779283434,-17.0268379126,2.9516498622,-33.5392106561,-17.0949571104,-7.96389574493,-1.96574052406,20.6440656573,9.3517821705,18.8621571854,0.642108624467,-0.250264642711,-1.73278119676,1.42202216053,-0.159873395219,2.12210275296,-2.05687158463,-3.00899107481,-5.51915203302,-8.23276321766,6.1975286324,-0.409045251395,10.8680215979,-1.37294460019,0.711408669016,-3.83295634384,-1.66185232049,0.318774382959,-0.927526407945,0.620496904746,0.291989079951,0.0767652812471,-1.41476484232,-0.45917402836,-2.03235670784,-1.30104992005,-0.737215113993,-0.26176096308,0.382336977294,1.54928576338,0.427613193749,0.308628258475,0.557405636206,-0.759512089602,0.448737577924,-0.365316976674,-0.0312901209034,-0.117094497529,-0.00852594549329,-0.0272541860184,-0.35487718675,-0.0341526139197,-0.036773085341,0.00251868902317,-0.136354333778,0.00658083239374,-0.0224306207363,0.43804943377,1.13093264606,0.739183433914,0.454757469862,-0.0421778585284,-0.468139497647,-0.511208579756,0.037463995799,-0.151510821882,0.189915838639],[-36340.6010406,-1574.39506348,-70.3300294405,-1893.10371658,-1318.16275191,1305.14194663,1166.65056179,701.62219015,-737.679736283,17.3296705095,953.248434183,67.8874774271,-804.851980649,-384.148561722,11.7286382909,-95.1522379338,-60.1714954629,-23.6803505102,-633.581741457,-468.771483114,-4.06163353042,-128.674060077,79.2949753549,-551.232152884,59.7275675211,75.3994876115,-116.03938618,137.37296155,-20.2923796371,192.140491114,-108.409366282,-204.046488942,-89.6730105467,-59.4079141343,266.157951714,6.95733130527,11.7698354094,43.5689381876,14.9540797536,-19.1324678715,-62.3318435328,-60.4841955195,-101.114405739,-38.7112429144,-31.8500905963,15.6374771379,-18.6231839956,-25.5259701035,-2.10999064472,0.648125857001,3.15381889058,-0.0364825838822,-16.8057133616,-8.71495642613,-16.9951062767,2.79094638638,-32.9881457713,-17.0425745192,-7.77433272839,-1.67552345574,20.5336409794,9.47772640138,18.8178778806,0.537797754999,-0.219793522519,-1.73067608182,1.38163862977,-0.103784539952,1.9778916581,-2.0419791938,-3.02549154549,-5.34755331218,-8.17689250596,6.31006960282,-0.363551544741,10.7989464362,-1.26426404632,0.714154556546,-3.77574455712,-1.54673263863,0.287312785922,-0.926091099399,0.591540656946,0.272424932751,0.0967304818411,-1.4619723651,-0.452650019362,-2.03249966547,-1.23942566536,-0.722651905702,-0.205581439812,0.412836509507,1.55434415648,0.467693691731,0.319560395783,0.580033538449,-0.720540891562,0.459841966865,-0.359274093016,-0.0350396992015,-0.11968143714,-0.0205608223858,-0.0316218103459,-0.347813764517,-0.0432322163888,-0.0320672794333,-0.00937408490195,-0.120918678352,0.00891679446771,-0.0100192543583,0.439161390767,1.12991557869,0.74577240389,0.457383154667,-0.0286015095443,-0.453755495521,-0.500384783544,0.0399078930834,-0.156708214929,0.189001600968],[-36408.2112474,-1528.54510734,-15.0476872752,-1927.48815277,-1308.96613623,1298.50934475,1176.02367813,691.996735502,-752.175666799,38.8275391973,939.339934889,82.8135663733,-820.701497771,-420.047356816,-5.64381334492,-91.6619395769,-55.8050985196,-24.264806668,-629.424811315,-474.341309572,-13.8612132994,-125.553084086,91.5358997625,-543.478747878,63.8812890961,74.9395473623,-113.173111315,134.427962174,-23.1948651252,191.847584257,-104.938064109,-201.672869029,-86.0302029515,-56.8268506616,260.378141887,7.25105089234,12.0605641718,44.1987284542,14.607868429,-20.6001772892,-61.5219048475,-59.8644215856,-100.606533775,-37.8237330141,-31.5442879158,15.0717384705,-18.1543911287,-25.1338022391,-2.04692765203,0.918983845268,3.48066983011,-0.214748498125,-16.625610356,-8.94604075663,-16.9846654747,2.65068889551,-32.4492240927,-16.9976160428,-7.56738548765,-1.39628740954,20.4140666255,9.61595193198,18.7858564673,0.434162929684,-0.177469807763,-1.7263698795,1.34036828294,-0.0467866861156,1.84292453614,-2.03263028064,-3.03475632513,-5.17718509264,-8.11774111133,6.42462620033,-0.319990234111,10.7349267817,-1.15640249146,0.722876838204,-3.71591345881,-1.43416196943,0.255273336077,-0.922495849646,0.564599184883,0.253058655333,0.117385017632,-1.50723541176,-0.446088996051,-2.0300722584,-1.17850872739,-0.706506880796,-0.149614327592,0.443335114607,1.56071445319,0.507784286079,0.331757443012,0.602968768578,-0.683065894468,0.469686977344,-0.353491236248,-0.0390564057045,-0.1215898321,-0.0327536116337,-0.0355272139279,-0.340099077481,-0.0520387274371,-0.0271721084568,-0.0204570953595,-0.105178087357,0.0116931808894,0.00228167605248,0.44038419195,1.12940438982,0.752241686348,0.459915302544,-0.0150165411793,-0.439717800038,-0.489934550337,0.0423971828137,-0.161783370013,0.188163801733],[-36463.7810465,-1479.55508428,34.0960203766,-1960.68508698,-1296.61476252,1294.97793422,1183.03130232,681.341815176,-766.113491989,60.5449530588,925.149566703,94.2124185039,-835.116603409,-454.160761639,-22.4270833692,-87.33480583,-53.1003416676,-24.579120744,-625.586723378,-479.283289832,-23.442243213,-122.468471791,103.181862182,-536.407434253,68.2720319155,74.1907274121,-110.757373985,131.642564127,-26.1052651614,191.585966505,-101.725594408,-199.274044877,-82.33776765,-54.1332207566,254.750125249,7.58611012502,12.3614746133,44.7463358265,14.1990550188,-22.1331502739,-60.7100585578,-59.3286543609,-100.069144888,-36.9709472139,-31.2005066129,14.5523468558,-17.749563127,-24.7782433627,-1.96375778723,1.21158590062,3.80769033423,-0.398323157584,-16.4544629521,-9.1728986119,-16.9954485844,2.53001709614,-31.9293910608,-16.9532793989,-7.34221514285,-1.12688186627,20.2873179813,9.76571682213,18.7703235909,0.332897054529,-0.124778939806,-1.72035765891,1.29742029109,0.00905591431068,1.71793820322,-2.0284326641,-3.03788048938,-5.00887262943,-8.05423082498,6.54177640566,-0.277110290288,10.6775563234,-1.05098379486,0.739002586245,-3.65405622779,-1.3250806726,0.223272701424,-0.916888461671,0.540096937792,0.233661026997,0.138196938042,-1.55047298812,-0.439404999549,-2.02555938744,-1.11848508633,-0.688618031645,-0.0939780326769,0.474296757331,1.56895946863,0.547564902426,0.345844016053,0.626282136888,-0.647290691121,0.47827161861,-0.348167083967,-0.0432491829803,-0.122735809002,-0.0449373055976,-0.039051758315,-0.331846681645,-0.0605425738944,-0.0221434677846,-0.0307658977907,-0.0891328043656,0.014854691995,0.0144516268686,0.441878330074,1.12960374622,0.758555039129,0.462549891726,-0.00155776723102,-0.426015605529,-0.480002261435,0.0449320317392,-0.166688080214,0.187422361759],[-36504.1792069,-1427.3920392,77.7360492698,-1991.52773649,-1280.1643809,1296.91327506,1186.93591378,670.205892181,-779.4569023,82.5109424835,911.24722548,101.744369991,-847.837359179,-486.6381385,-38.5298427704,-82.2632740627,-52.0370545277,-24.5372550607,-622.140629357,-483.448438524,-32.8756170186,-119.596623422,114.053407568,-530.082580554,72.8314366915,73.162571861,-108.828551786,129.072635607,-28.974116915,191.303927394,-98.8372438361,-196.931334961,-78.6239279936,-51.31126733,249.340305936,7.95085689364,12.6633428175,45.1978006219,13.7383709467,-23.7221993573,-59.9192145693,-58.892087633,-99.5192483383,-36.1679637488,-30.8052908097,14.0855642096,-17.4158611689,-24.4746018569,-1.86035888762,1.5193265469,4.12808116371,-0.584975572614,-16.2966178064,-9.39650267615,-17.0265519637,2.42574961029,-31.4345761672,-16.9042028893,-7.09893160629,-0.866228528886,20.1535401567,9.92542643533,18.7741034715,0.235651006996,-0.0637760467337,-1.71323163312,1.25233012221,0.0617553563937,1.60379880872,-2.0287714254,-3.03610388274,-4.84324849675,-7.98549231334,6.6619484999,-0.233706879313,10.6276326432,-0.949525241392,0.763420325941,-3.59056245867,-1.22035652818,0.191917668547,-0.909591845566,0.51831901544,0.214003562497,0.158617558879,-1.59149372673,-0.432445208873,-2.01937749912,-1.05939873221,-0.668848037178,-0.0387574953577,0.506147228957,1.57944459469,0.586654346259,0.362210406941,0.650034195475,-0.613431370551,0.485579371719,-0.343498477321,-0.0475161841827,-0.12307276935,-0.0569607600612,-0.0423210515549,-0.323175833693,-0.0687034193121,-0.0170330306539,-0.0403072917545,-0.0727587748924,0.0183453228254,0.0265045088013,0.443784178349,1.13066215194,0.764668235713,0.465405535032,0.0116692465361,-0.412658949647,-0.470694397437,0.0474866261148,-0.171369463364,0.186788709531],[-36526.0134604,-1370.70085293,116.344096993,-2018.84726815,-1258.60487584,1305.91611182,1186.90644448,659.177242943,-792.15544371,104.689658951,898.12883364,105.17078301,-858.567863824,-517.558201339,-53.7371240944,-76.5570062931,-52.5825611581,-24.0702038209,-619.135394123,-486.674227743,-42.2254114558,-117.054472549,123.978670342,-524.540361961,77.4871237319,71.8722996803,-107.402068714,126.770748535,-31.7545964653,190.961877888,-96.325142141,-194.723708779,-74.9104117832,-48.3570564316,244.220242677,8.33554371355,12.9603228031,45.5452616316,13.2391438775,-25.3578167606,-59.1709949527,-58.5684316487,-98.9749988742,-35.4231804833,-30.350762241,13.6839546676,-17.1582746097,-24.2374799313,-1.73687284454,1.83657137803,4.43568885301,-0.772411248784,-16.1567764076,-9.61734350699,-17.0772179971,2.33450028876,-30.9683652449,-16.8463286383,-6.83671651977,-0.613705359024,20.0121587217,10.0923775837,18.7992788936,0.144056531997,0.00343466885509,-1.70571506319,1.20480909064,0.109561892758,1.5011511458,-2.03285353075,-3.03070022022,-4.68070574507,-7.91092804383,6.78584068963,-0.188899038775,10.5857308075,-0.853661776141,0.796691878142,-3.52572019877,-1.12073074446,0.161737499059,-0.901011908014,0.499392855723,0.193899704946,0.178192715675,-1.63013112188,-0.425046131925,-2.01193991549,-1.00124577061,-0.647097377738,0.0160070576268,0.539186652669,1.59244353182,0.624575412577,0.381098628069,0.67426225045,-0.58165991418,0.491568927682,-0.339684912249,-0.0517781856594,-0.122585680659,-0.0686986195345,-0.045454382509,-0.314197482188,-0.0764926676494,-0.0118778445701,-0.0490884130928,-0.056046428874,0.0221154970023,0.0384635426899,0.446207898867,1.1327077864,0.770527151126,0.468566532461,0.0245681764348,-0.399658206607,-0.462109913097,0.0500117506623,-0.17577656088,0.186272860158],[-36527.4548535,-1307.71226677,150.930016365,-2041.78546246,-1231.57799359,1322.41471332,1182.08873729,648.8621547,-804.180189878,126.853468019,886.152016116,104.499281658,-866.983945433,-546.840285309,-67.7880841221,-70.2996768452,-54.7075004512,-23.1075254921,-616.598078993,-488.831688266,-51.5733768255,-114.894554055,132.784346065,-519.743611292,82.1790378689,70.3442603277,-106.469723422,124.773627435,-34.410458899,190.540011818,-94.2234741913,-192.71399564,-71.2104256528,-45.2775653343,239.448021381,8.73416891898,13.2501050296,45.7890982392,12.7148679864,-27.0293515441,-58.4822050452,-58.3684522517,-98.4555032835,-34.7377773309,-29.8353422914,13.3652168886,-16.9789518667,-24.07627639,-1.59396300378,2.15927116386,4.7255727818,-0.95862382953,-16.0387000257,-9.8358528747,-17.1470307058,2.25263221827,-30.5317901797,-16.7769729923,-6.55452879643,-0.369695726254,19.8617191918,10.262888251,18.8464448267,0.0594250062679,0.0750267465449,-1.69868581465,1.1547182441,0.151225321859,1.41029390768,-2.03983629397,-3.02297268018,-4.521391185,-7.83036275887,6.91426588782,-0.142301741677,10.5522727271,-0.764708015011,0.839021581999,-3.45959669104,-1.02683042128,0.133150268226,-0.891554720009,0.483251653573,0.173224765684,0.19662985654,-1.66632210581,-0.417066928388,-2.00370257549,-0.943998476411,-0.623374114516,0.070339242294,0.573561010281,1.60807674571,0.660812978968,0.402562851918,0.698915596951,-0.552089515381,0.496188075993,-0.336853912398,-0.0559769836578,-0.12129900479,-0.0800671753297,-0.0485504123549,-0.305017591157,-0.0839034123633,-0.00669430366729,-0.0571339247936,-0.0390013274701,0.0261182851822,0.0503515417899,0.449207744609,1.13581171242,0.776062145357,0.4720811734,0.0370806524425,-0.387023518136,-0.454305113314,0.0524406242317,-0.179865961028,0.185869864618],[-36510.2956367,-1238.56601927,182.38038463,-2059.86876817,-1199.79436652,1345.74536927,1172.05273898,639.514871537,-815.399401423,148.606598438,875.526913446,99.9687856204,-872.842226457,-574.397366815,-80.4635481274,-63.4959757096,-58.3710739845,-21.5663604553,-614.523541223,-489.871298698,-61.0022425185,-113.142883701,140.312723099,-515.60561501,86.8694869782,68.6184796684,-105.998297779,123.107369188,-36.9200695594,190.037466613,-92.5571099276,-190.947602416,-67.5239579253,-42.0889216663,235.068532816,9.14320822167,13.537148298,45.9391494947,12.1780332728,-28.7232929329,-57.863272325,-58.2992856855,-97.9816145698,-34.1055911356,-29.2641794828,13.1465871786,-16.87921661,-23.995972918,-1.43406630538,2.485307996,4.99443545679,-1.14181074858,-15.9437509187,-10.0520192888,-17.2356779332,2.17635418264,-30.1240636962,-16.6952062705,-6.25112334756,-0.135805796213,19.7003904114,10.4333812125,18.9146129039,-0.0177779184076,0.149423782157,-1.6931278188,1.10213556055,0.186358782166,1.33125457774,-2.04880405314,-3.01428165495,-4.3651826438,-7.74417551409,7.04814465607,-0.0940883565746,10.5274285292,-0.683694859419,0.890124412297,-3.39221865299,-0.939168832574,0.106405260544,-0.881670551268,0.469619049559,0.151949726091,0.213828202798,-1.70011542413,-0.408307676819,-1.99515001436,-0.887599143987,-0.597839413168,0.124326684712,0.609193787807,1.62624005161,0.694892791065,0.426401713057,0.72392771756,-0.524823599779,0.499418830785,-0.335100917757,-0.0600586118888,-0.11930295605,-0.0910378206244,-0.0516848408863,-0.29574641082,-0.0909475491565,-0.00146705163667,-0.0644744628803,-0.0216404815652,0.0303009245983,0.0621883722106,0.452802882508,1.13998184796,0.781202711092,0.475949652314,0.0491920603571,-0.374784325311,-0.447289596755,0.0547033693948,-0.18360740962,0.185571829033],[-36478.8662548,-1164.54791647,209.890588428,-2072.81436617,-1164.72988602,1374.56000924,1157.05021183,631.056824141,-825.571165017,169.484629277,866.283390247,91.9441836393,-876.052689519,-600.259501916,-91.5282165002,-56.0788016083,-63.5131159247,-19.3857391933,-612.8955338,-489.811435962,-70.5538145414,-111.797302836,146.455388921,-512.020880891,91.5375470939,66.7437060164,-105.931729276,121.790323569,-39.2726609331,189.465000144,-91.346295244,-189.455007213,-63.8364856843,-38.8164833939,231.128115328,9.55928422818,13.8324592329,46.0116544988,11.6409419935,-30.4253382708,-57.3197050686,-58.3639833063,-97.5711081178,-33.5136687839,-28.6483324938,13.0419152107,-16.8616299594,-24.00025363,-1.26100713273,2.8141214042,5.24015742565,-1.32064592101,-15.8710670705,-10.265047562,-17.3426206475,2.10268675108,-29.7436351056,-16.6018875654,-5.92510578237,0.0852073948574,19.5270808707,10.6009033255,19.0016329023,-0.0878386296369,0.225061115508,-1.6899806656,1.04734754673,0.215261864075,1.26388600672,-2.05891710018,-3.0059465843,-4.2118374815,-7.6531189627,7.18837386262,-0.0450466338291,10.5110714959,-0.611751443781,0.949216445059,-3.32387798153,-0.858109100042,0.0815782708588,-0.871826003191,0.458048044944,0.130143698215,0.229796197719,-1.73162469409,-0.398520344433,-1.98672885023,-0.831966867546,-0.57074900287,0.178047713848,0.645701551204,1.64667815401,0.726357566268,0.452249186316,0.749264316372,-0.499991303808,0.501303712932,-0.334549806111,-0.0639663232972,-0.116736203235,-0.101625138821,-0.0549195122067,-0.286491224231,-0.0976471637856,0.00384756309079,-0.071148123844,-0.00401080044561,0.034602621968,0.073979130935,0.456970655189,1.14518434367,0.785879626075,0.480137850107,0.0608919127315,-0.363000975813,-0.441058722393,0.0567347244407,-0.186976251953,0.185384708205],[-36437.6821226,-1086.4423206,231.028794866,-2080.45874832,-1127.94316788,1407.17675606,1138.05203085,623.356570429,-834.517205327,189.041801989,858.339606581,80.9015369814,-876.704823506,-624.499718828,-100.756430455,-47.967549126,-70.0477801943,-16.5423869971,-611.69550045,-488.705527723,-80.2176023097,-110.800209004,151.182582528,-508.848775251,96.1722759924,64.7673606586,-106.200848694,120.827348598,-41.4601634068,188.840438962,-90.592903242,-188.250610712,-60.1181596274,-35.4964057584,227.670534683,9.98097071735,14.147240878,46.0267853437,11.1149476846,-32.119970705,-56.8551490403,-58.5603120144,-97.2343786543,-32.9434125934,-28.0012022124,13.0615786275,-16.9276955202,-24.0904480665,-1.07908738363,3.14583583513,5.46126057714,-1.49389108084,-15.8181684006,-10.4738805443,-17.4665607998,2.03007461754,-29.3877802189,-16.4990798926,-5.57531133484,0.2895588854,19.3422860723,10.762985917,19.1048722477,-0.1513955343,0.300484079965,-1.69003655288,0.990740385924,0.238729034718,1.20770783539,-2.06933731698,-2.9991996342,-4.06113295932,-7.55812297948,7.33573293999,0.00350250703925,10.5029931405,-0.549938194444,1.01512469156,-3.25516271463,-0.783938970477,0.0586319177982,-0.862461400277,0.448019461162,0.107921575456,0.244602097874,-1.76102008467,-0.387465590931,-1.97888841882,-0.777033475101,-0.542385361244,0.231576555886,0.682485912511,1.6690993403,0.754752240172,0.479720099819,0.774851560023,-0.477709543043,0.501944936831,-0.335295205872,-0.0676559617847,-0.113757321715,-0.111862929639,-0.0583062529465,-0.277369456511,-0.104027906864,0.00930862880582,-0.0772233337276,0.0138204196699,0.0389563562557,0.0857259136832,0.461638243008,1.15137160387,0.790010534436,0.484618503849,0.0721523031302,-0.351759535132,-0.435603199577,0.0584689739188,-0.189958387041,0.18532365571],[-36390.4235034,-1005.59236886,241.559518024,-2082.77607916,-1090.76641462,1441.74201314,1116.10182873,616.067425219,-842.217782788,206.925452192,851.530717626,67.292486415,-875.130502454,-647.168626815,-108.080839199,-39.1199897809,-77.8183918845,-13.0664319977,-610.914698663,-486.623817091,-89.9181969917,-110.07834114,154.563487502,-505.905351483,100.769525296,62.7430369309,-106.73603356,120.216451904,-43.4676803962,188.188178065,-90.2710270547,-187.332135672,-56.3240015216,-32.1747262588,224.729846398,10.4123007766,14.4901534992,46.0080374011,10.6129873212,-33.7861360596,-56.4741188707,-58.8810968354,-96.9724757356,-32.3726740296,-27.3369617201,13.2102986521,-17.0756393038,-24.2674397031,-0.892730929083,3.48052407595,5.65714956616,-1.65886089547,-15.7816325123,-10.6779345137,-17.6049770427,1.95896418648,-29.0525869671,-16.3896260513,-5.20181986173,0.47275928549,19.1474257993,10.9176572607,19.2221254914,-0.209192933874,0.374411148273,-1.69381119556,0.932857604265,0.257958634687,1.16172870414,-2.07900496962,-2.99499831652,-3.91307668766,-7.46045760599,7.49062496165,0.0497444940635,10.5026308642,-0.498943235431,1.08645013033,-3.18699676026,-0.716959117003,0.0374416876905,-0.854026335174,0.43900883015,0.0853756893201,0.25834644798,-1.7885043262,-0.374953168896,-1.97214261196,-0.722818840618,-0.512998708388,0.284958047584,0.718838684063,1.69313362787,0.779696725951,0.508480401613,0.800537835419,-0.45804295578,0.501502277237,-0.337364186234,-0.0711317942625,-0.110537803551,-0.121794482723,-0.0619129916205,-0.268541164926,-0.110104722294,0.0149623831884,-0.082793520005,0.0317771150795,0.0433258762482,0.0974459358997,0.466671323718,1.1584783007,0.79351091664,0.489399872712,0.0829229670608,-0.341157974182,-0.430915567516,0.0598266604425,-0.192557763166,0.185399481618],[-36339.551398,-924.999848961,238.420007991,-2080.09663127,-1054.08609924,1476.99217971,1092.38937164,608.814488723,-848.857781442,222.932481389,845.669103149,51.581319504,-871.694755378,-668.273972272,-113.468394602,-29.5596528468,-86.6173217007,-9.0431828877,-610.558381589,-483.600516845,-99.5003088644,-109.544435135,156.71484957,-502.993945106,105.325590553,60.7203516414,-107.475360432,119.958659543,-45.2707309293,187.548817595,-90.3231399025,-186.691678956,-52.3927586978,-28.9070793399,222.336584563,10.8639009146,14.8669869368,45.979154438,10.1500036127,-35.3977054113,-56.1807867092,-59.3122146226,-96.7799146341,-31.773867674,-26.6749860524,13.4881026485,-17.3010251944,-24.5326548074,-0.70508999655,3.81785645831,5.82790327545,-1.8121603005,-15.7576364559,-10.8770323022,-17.7542676054,1.89139340522,-28.7332523658,-16.2777800024,-4.80575567132,0.631044530659,18.9447173757,11.0639495015,19.3510110753,-0.261846399983,0.445721962335,-1.70146058299,0.874194019589,0.274313118509,1.12445878809,-2.08696740661,-2.99394066687,-3.76774845269,-7.36178250215,7.65346726672,0.0916593537586,10.5092277108,-0.459175092338,1.16161551519,-3.12074780899,-0.657401181257,0.0177889336718,-0.846886743614,0.430529858184,0.062525684129,0.271116781816,-1.81435392912,-0.360860790389,-1.96702773535,-0.669415555256,-0.482808441403,0.33826818858,0.753946905431,1.71839751152,0.800886658964,0.538250062533,0.82609767537,-0.441063492995,0.500193786801,-0.340763270857,-0.0744532283786,-0.107231952209,-0.131464178141,-0.0658359842421,-0.260186402256,-0.115892428208,0.0208371408813,-0.0879539019589,0.049751726329,0.0477132289965,0.109193261768,0.471891791522,1.16645532172,0.796311767903,0.494531344064,0.0931212439675,-0.331299882748,-0.426990160916,0.0607338825025,-0.194779402193,0.185630280605],[-36287.0933101,-845.935335362,220.973212321,-2073.25605651,-1018.09433262,1511.85071124,1068.17251418,601.134066284,-854.917558734,236.980481316,840.499176024,34.4773418949,-866.658420157,-687.568742625,-116.966724289,-19.4187002145,-96.2458116,-4.57371845976,-610.630319485,-479.65161457,-108.757782095,-109.109561135,157.748071198,-499.923036729,109.821156086,58.7211330077,-108.357212219,120.050571885,-46.8466893445,186.990969252,-90.6697472032,-186.296879703,-48.2760428292,-25.7466770973,220.507359499,11.348695999,15.2751339973,45.965273611,9.73999000199,-36.9265680566,-55.9725688699,-59.8331162156,-96.6423584186,-31.1191264865,-26.0371981893,13.8940406625,-17.5946842692,-24.8839957672,-0.517591977171,4.15565986387,5.97431295399,-1.95123041697,-15.7419350758,-11.0705422056,-17.9101350005,1.83238057595,-28.4251940136,-16.1671459362,-4.39018067135,0.762303559491,18.7361352383,11.201382813,19.4879571495,-0.309575631661,0.513201451899,-1.71304768045,0.814802393992,0.289267900122,1.09429318182,-2.09246840246,-2.99573356063,-3.62520228381,-7.26351704811,7.82436684792,0.127573909832,10.522179094,-0.430389388149,1.23903436071,-3.05788896405,-0.605421017086,-0.000472019216645,-0.841275925454,0.422074944907,0.0392395234885,0.28302629627,-1.83894729169,-0.345100184859,-1.9640159115,-0.616887101531,-0.451930338017,0.391577441632,0.78706217267,1.74453816355,0.81817210301,0.568726912749,0.85118334815,-0.426866581045,0.498217344674,-0.345417674394,-0.0776743670656,-0.103943963699,-0.140922879819,-0.0702138112962,-0.252482281106,-0.121445451415,0.0269494200226,-0.0928045436424,0.0676423805274,0.052162868869,0.121052991699,0.47714007534,1.17526534338,0.798398955568,0.500088290553,0.102672409711,-0.322283306994,-0.423797048188,0.0611372339465,-0.196613452711,0.186023230433],[-36236.4628926,-768.900787796,189.924839097,-2063.26782568,-983.455469238,1545.11047435,1043.98475286,592.528392237,-860.912296687,248.840502388,835.608683707,16.6497875695,-860.303279776,-704.682575279,-118.880399705,-8.86288378506,-106.516039399,0.202292638778,-611.208664307,-474.843081418,-117.508353789,-108.720482352,157.738269202,-496.529254838,114.241455022,56.7573452198,-109.315872288,120.468821495,-48.1865254401,186.579884569,-91.2328817598,-186.106324666,-43.9692687582,-22.7424063356,219.241635468,11.8812302241,15.7121921377,45.9924794446,9.39791036558,-38.3461434205,-55.8441215906,-60.4234198518,-96.5407209605,-30.3896019136,-25.4445102398,14.4242133836,-17.9401030022,-25.3162703804,-0.330804664318,4.49196483757,6.09800403018,-2.07243346913,-15.7297619898,-11.2572943452,-18.0684266279,1.7888771467,-28.1260545379,-16.0603945207,-3.96163770946,0.866180975158,18.5225752,11.3295133715,19.628303606,-0.352580422783,0.575740279308,-1.72866271555,0.754986548089,0.304592039048,1.06988907626,-2.09489065251,-2.99944106411,-3.48575632499,-7.16679731517,8.00227970337,0.156556702826,10.5406839044,-0.41144967352,1.31701719039,-2.9998377716,-0.561164043256,-0.0175050935515,-0.837379851887,0.413115212286,0.0153634971646,0.294235839217,-1.8625577769,-0.327542102882,-1.96349081739,-0.565242291951,-0.420394999953,0.444821828772,0.817612575135,1.77116485513,0.831650598346,0.599535876633,0.875363238692,-0.41552247604,0.495720352079,-0.351090195845,-0.0808417462738,-0.100770136426,-0.150216050995,-0.0752042202619,-0.245590997598,-0.12681602623,0.0333279208103,-0.0974486119182,0.0853831917129,0.0567388137685,0.133129227962,0.482306048893,1.18484891318,0.799845369051,0.506143194115,0.11154226112,-0.314197676919,-0.421278192589,0.0610182343394,-0.198032128348,0.186564313655],[-36191.6393731,-694.45452373,146.528789533,-2050.89952404,-951.464263533,1575.58799597,1019.8124338,582.514561238,-867.300076032,258.211950611,830.470330594,-1.33022848812,-853.08124721,-719.36555691,-119.898348741,1.91490547482,-117.210925478,5.09500463725,-612.456896269,-469.330351876,-125.615617787,-108.353470423,156.748387318,-492.694588595,118.581695894,54.8363847248,-110.27726518,121.172027976,-49.2936317059,186.368861758,-91.9334401649,-186.081477435,-39.5134362008,-19.946761235,218.524308283,12.4761750414,16.1758671949,46.089029587,9.14044566473,-39.6324174248,-55.7893970907,-61.0631523791,-96.4524555832,-29.5754290697,-24.9144771351,15.0680468802,-18.3116949067,-25.8233102784,-0.145036513038,4.82511268817,6.2012738727,-2.17056793761,-15.7158945441,-11.4352050786,-18.2249905211,1.7699621486,-27.8355174153,-15.9594012164,-3.53048883442,0.943977013697,18.3047381397,11.4484794038,19.7664541354,-0.39113726849,0.632417581639,-1.74861580527,0.695348776154,0.322598860712,1.05025507784,-2.09382192188,-3.00376958388,-3.34989842911,-7.07251249271,8.18497940232,0.178499482214,10.5636747481,-0.400350363734,1.39333471162,-2.94818292681,-0.524802849371,-0.033530884646,-0.835374406667,0.403123673626,-0.00931351946353,0.304960455245,-1.88536301126,-0.308065751513,-1.96579901035,-0.514416833542,-0.388125355255,0.497788389818,0.845193114207,1.79779819795,0.841668394557,0.630240301379,0.898168256049,-0.407000201948,0.492876663034,-0.357358039754,-0.0840007418567,-0.0978007395249,-0.159381384025,-0.080980345345,-0.239662462148,-0.132056034016,0.0400087767744,-0.101994379479,0.102946484348,0.0615038645955,0.145546073344,0.487325695684,1.1951337307,0.800813032554,0.512781708902,0.119740861373,-0.307126363957,-0.419358580585,0.060400383607,-0.199002869398,0.187230743591],[-36156.1240421,-625.2389504,92.9931785096,-2036.57564396,-923.619431058,1602.67509781,995.980021284,570.755622369,-874.404558295,264.887060234,824.480363556,-18.9506179508,-845.567614336,-731.513615022,-120.968078112,12.7175029571,-128.106382324,9.87821963087,-614.574281003,-463.296114204,-132.936034177,-108.023757836,154.837827906,-488.407951784,122.841247026,52.9557637331,-111.164036625,122.113920903,-50.1781959049,186.400124762,-92.6919780921,-186.198505015,-34.9761376119,-17.4130350418,218.3473488,13.1476104028,16.6625135538,46.2832723618,8.982781947,-40.7645732531,-55.8039110728,-61.7310431734,-96.3521373939,-28.6715139301,-24.4617721207,15.8100798902,-18.6776214076,-26.4000398357,0.0399701568826,5.15345492596,6.28649849974,-2.24053219562,-15.6948655801,-11.6017491734,-18.3755734648,1.78620227592,-27.5540840137,-15.8655457942,-3.10893245923,0.99940415186,18.0841418201,11.5599958738,19.8962891572,-0.425475115912,0.682503228262,-1.77346954446,0.636374504956,0.345950257496,1.03462215598,-2.089125506,-3.00724452069,-3.21800287944,-6.98117309665,8.36965068097,0.193882587479,10.5898892147,-0.394743362287,1.46521102842,-2.90488786095,-0.496417690343,-0.0488190335029,-0.835382288137,0.391614757498,-0.0350938069962,0.315425159098,-1.90751630589,-0.286606368812,-1.97127449718,-0.46429612806,-0.354917680807,0.550155521609,0.869483492811,1.82390757896,0.848741718799,0.660398895598,0.919159428934,-0.401219769193,0.489892061961,-0.363684157273,-0.0872024064456,-0.0950852412715,-0.168438420646,-0.0877138799566,-0.234834517321,-0.137224417255,0.0470266441833,-0.106553545615,0.120313359989,0.0665098610573,0.158442360173,0.49215705764,1.20605585405,0.80152320295,0.520109774521,0.127295206305,-0.301140634266,-0.417979929886,0.0593704509195,-0.199481060683,0.188020729549],[-36130.5070424,-564.508038095,35.2031227455,-2020.19586292,-900.486030808,1626.96491071,974.073814173,557.61970515,-882.544651948,269.00141221,816.975812511,-35.5624809849,-838.078253913,-741.121977618,-123.084580509,23.3064995896,-138.996473693,14.304971447,-617.730856936,-456.869016058,-139.29619432,-107.744861245,152.02418267,-483.709437825,127.007914762,51.0913672501,-111.909772244,123.244510114,-50.8528407288,186.707550139,-93.4060453347,-186.449232153,-30.4142256756,-15.1948744526,218.714751509,13.9098523115,17.1607094556,46.5996851915,8.93460915673,-41.727389472,-55.8810514812,-62.3971037328,-96.2121474799,-27.6699236672,-24.1031938823,16.634814878,-19.004592318,-27.0398113961,0.226292777536,5.47424468832,6.35561678096,-2.27858781676,-15.6617536452,-11.7545611353,-18.5157118349,1.84844184832,-27.2808551739,-15.7807420735,-2.70779107544,1.03783806704,17.8635076529,11.6669081507,20.010262779,-0.45553185751,0.725600799987,-1.80382345342,0.578058226223,0.376915740172,1.02211627942,-2.08131374286,-3.00823613731,-3.08997933834,-6.89314428217,8.55361057615,0.203185854822,10.6181096177,-0.392304631467,1.52948462251,-2.87233778044,-0.475944163432,-0.0636139806104,-0.837284121654,0.378165385176,-0.0623730016873,0.325812050803,-1.92921793918,-0.263311995833,-1.98019372528,-0.414756241605,-0.320547097966,0.601702134345,0.890107031049,1.8490735416,0.853452720656,0.689573808462,0.937818303272,-0.398132578951,0.48698890165,-0.369479221598,-0.09051036246,-0.0925945391064,-0.177374855619,-0.0955583341577,-0.231217788477,-0.142387743835,0.0543839449116,-0.111251988089,0.137441578781,0.0718024977106,0.171978000262,0.4967442174,1.21756546789,0.802183382959,0.528248608966,0.134205679997,-0.296294607748,-0.417079157611,0.0580710052769,-0.19939749319,0.188935171639],[-36111.8131271,-514.226801809,-15.3610798762,-2000.71971237,-881.234686362,1649.98511008,956.921857685,544.126593248,-892.01274306,271.082322705,807.227104417,-50.2077365299,-830.569240189,-748.136335601,-127.294978768,33.3937285825,-149.685302067,18.13438478,-622.046349439,-450.130983355,-144.533453674,-107.526060876,148.233972049,-478.646237629,131.053852059,49.2053776185,-112.458276154,124.508502835,-51.3333596165,187.323426509,-93.9442525039,-186.834021807,-25.8740038405,-13.3516657643,219.632704581,14.7782795638,17.6507541344,47.0611326562,9.00077918656,-42.5096483649,-56.0093780388,-63.0220836765,-96.0031070469,-26.5593269919,-23.8605098393,17.5313550588,-19.2569360112,-27.7315093297,0.417920511105,5.78362252685,6.41033565944,-2.28187403066,-15.6117991548,-11.8915034959,-18.6409517305,1.96783366092,-27.0128132897,-15.707275357,-2.3367401543,1.06575398825,17.6454494167,11.7720230939,20.0980187492,-0.481005387565,0.761761909031,-1.8403677816,0.519900818932,0.417342136762,1.0118015616,-2.07146449969,-3.00481463995,-2.9652274241,-6.80860309569,8.73422732055,0.206626683476,10.6471849785,-0.390602433036,1.58247590543,-2.85313409341,-0.463306691174,-0.0781329081513,-0.840697761365,0.362390311137,-0.0916419575208,0.33632852588,-1.95072342336,-0.238508611406,-1.99276956521,-0.36569596922,-0.284777788648,0.652336376275,0.906591901631,1.87294517106,0.85637113509,0.71723085692,0.953420797034,-0.397771876038,0.484372328303,-0.374067991216,-0.0940100348544,-0.0902294706886,-0.186148167739,-0.104641607386,-0.228887707033,-0.147620640209,0.0620667023739,-0.116231397402,0.154271014355,0.0774334849519,0.186337274305,0.501006207747,1.22960029209,0.802958660712,0.537316051271,0.140463165802,-0.292637544798,-0.41655400783,0.056674533683,-0.198640825479,0.189952953879],[-36095.6628395,-475.054820708,-42.6763963033,-1976.21540748,-864.411559759,1673.80553357,948.494372908,531.656923449,-902.962038717,271.764507142,794.411116802,-61.7446353063,-822.85167821,-752.474505097,-134.847297702,42.685750749,-159.996212241,21.1008112825,-627.598789867,-443.147496915,-148.482252915,-107.412625282,143.310441465,-473.297524587,134.94379205,47.2544327698,-112.759139098,125.84122534,-51.63817318,188.278890661,-94.1729643496,-187.368750362,-21.4034006774,-11.9445603657,221.119135409,15.7674730109,18.1111372591,47.691307503,9.18149355878,-43.1033458176,-56.1748426523,-63.5641826708,-95.6971639666,-25.3299718585,-23.7562371457,18.4929720871,-19.3949200153,-28.4643947943,0.619633560482,6.07776860538,6.45269836753,-2.24832230073,-15.5406448543,-12.0107352107,-18.7468439394,2.15576735428,-26.7457627811,-15.6474102963,-2.00428854074,1.09114158261,17.4313295812,11.8779812042,20.1473979004,-0.501533793493,0.791257503316,-1.88394222138,0.461030097815,0.468920734731,1.00261869566,-2.06077439837,-2.99489024851,-2.84278489293,-6.72752849749,8.90868034736,0.204475002309,10.6756878572,-0.387271679385,1.61995809979,-2.84992228199,-0.45842063574,-0.0926115502925,-0.845158944211,0.343911213981,-0.123471802102,0.347206459438,-1.97233969276,-0.212526539098,-2.00919463259,-0.316969571965,-0.247340526679,0.702028625382,0.918463643776,1.89513701414,0.85812259709,0.742695399668,0.965206113297,-0.400195223135,0.482253352744,-0.376708389608,-0.0977915096853,-0.0878636046135,-0.194695180844,-0.115069308722,-0.227893152112,-0.153018180137,0.0700686994992,-0.121635546269,0.170755347004,0.0834590405938,0.201727961972,0.504853939721,1.2420821084,0.803998190679,0.547405420472,0.146079159385,-0.290223265638,-0.416271233816,0.0553735949781,-0.197065786028,0.191041975395],[-36077.3730613,-444.894469276,-44.4999128836,-1947.1335274,-848.064560129,1699.28560704,949.310979718,520.340452602,-915.779214161,271.587330886,778.516042793,-69.5187862835,-814.961312217,-754.262511059,-145.809091843,51.0550062082,-169.819150701,23.1216808876,-634.203308817,-435.963845449,-150.993736249,-107.324512308,137.411132514,-467.740613661,138.684759146,45.1904276117,-112.796802507,127.24118224,-51.7868644016,189.60852184,-94.0311438864,-188.013612594,-17.0334451724,-11.0057020848,223.104245476,16.8866812483,18.524283183,48.4922355946,9.46679282251,-43.5023495973,-56.3592179413,-64.0046870948,-95.2778535194,-23.9754488211,-23.8051384631,19.4923723821,-19.4069490953,-29.2340349905,0.832084253867,6.35356630391,6.48492638148,-2.18350246936,-15.4440371151,-12.1097896004,-18.8285848101,2.4166607918,-26.4759999642,-15.6024330075,-1.71569193549,1.11688043579,17.2196563307,11.9869867759,20.1537606051,-0.517162913173,0.814250768854,-1.93373730955,0.399848976816,0.533143903244,0.993214346581,-2.04854409462,-2.97654746483,-2.7217486614,-6.64946426703,9.07587295478,0.19765452544,10.7014335999,-0.380515193444,1.63967950063,-2.8628698481,-0.460931629698,-0.107024451916,-0.850219857144,0.322600969037,-0.15803763681,0.358594853642,-1.99444263058,-0.185324689401,-2.02912457312,-0.26834969163,-0.207990193833,0.750905907007,0.92589285697,1.91520498266,0.859350928862,0.765181423264,0.973204523612,-0.405455335526,0.480835372944,-0.377329893874,-0.101835961837,-0.0853644079599,-0.203033452658,-0.126810929835,-0.228260309769,-0.158713383972,0.0783019769081,-0.127518695935,0.186877242144,0.0899078099058,0.218241094402,0.508293877164,1.25492429425,0.805455303648,0.558394760581,0.151118750142,-0.289093192795,-0.416064439745,0.054176254172,-0.194681518787,0.192184237572],[-36052.8151029,-419.737800556,-31.7478343182,-1916.35764309,-830.431605232,1726.12187108,955.980429567,509.601736742,-931.101583461,270.896046353,760.42840982,-73.5377291183,-807.146803986,-753.910321494,-159.087028946,58.5457251168,-179.112081044,24.2917389596,-641.465841916,-428.614841323,-151.971770709,-107.04614464,130.997906148,-462.057356929,142.323826395,42.9699625194,-112.585534273,128.76249283,-51.7927326597,191.346942951,-93.5344683844,-188.686733565,-12.7901561768,-10.5507297747,225.429650775,18.1388084309,18.8767280511,49.4462574507,9.83957723303,-43.7005420297,-56.5437723367,-64.3486444791,-94.7422444305,-22.495019175,-24.0149394937,20.4807135052,-19.3102236458,-30.0444742588,1.05110626344,6.60875622208,6.50896694157,-2.10016952695,-15.3173182012,-12.1853141196,-18.8811354863,2.74812371415,-26.2009119677,-15.5733041598,-1.47444324023,1.13997878122,17.0060222613,12.1008172389,20.1200677823,-0.528268707034,0.830651484967,-1.98735907361,0.334211926696,0.611377205658,0.982146731101,-2.03195536599,-2.94825654795,-2.60143783223,-6.57373234879,9.23631412483,0.187706782294,10.7213776366,-0.368964083115,1.64107309988,-2.88971001454,-0.470494001632,-0.121040594961,-0.855527995042,0.298569970911,-0.195143598749,0.370565154611,-2.01746478375,-0.156524598945,-2.05166901495,-0.219520543933,-0.166547802432,0.799168467151,0.929665214001,1.93254366868,0.86068885299,0.783769749,0.978269714926,-0.413633821767,0.480354482656,-0.376529054087,-0.106008461567,-0.082603703641,-0.21126262921,-0.139715466025,-0.230018531275,-0.164872121914,0.0866074045298,-0.133836065082,0.20264320921,0.0967818960655,0.235843119562,0.511416106399,1.26803090826,0.807507140336,0.569934154624,0.1557193403,-0.289302250632,-0.41574658577,0.0528977068398,-0.191647060949,0.193380840779],[-36020.0343103,-396.274175958,-11.9787829797,-1886.3281792,-810.616829256,1753.4107681,965.194765423,499.151993958,-949.382374029,269.866663971,740.885061777,-73.9989060676,-799.624857172,-751.695751084,-173.826261351,65.2392330205,-187.868258903,24.6830793317,-649.044963744,-421.175810231,-151.366451418,-106.437932178,124.406635345,-456.375997187,145.898733771,40.5709927083,-112.129898783,130.440899271,-51.6749194813,193.523860621,-92.723413043,-189.329728027,-8.72460460845,-10.5939354064,227.944151017,19.5234798816,19.1602430933,50.5410576863,10.2864400769,-43.6927930414,-56.7109162166,-64.6026742408,-94.0912950686,-20.8976641573,-24.3925732935,21.4122099596,-19.1205122594,-30.9028949192,1.27190727143,6.84178724744,6.5272270786,-2.00995590114,-15.1548389082,-12.2337161467,-18.9002055923,3.1482740495,-25.9193717214,-15.5610310961,-1.28583310367,1.15805371329,16.7829394878,12.2207927878,20.0481693017,-0.535329312057,0.840007676942,-2.04266793857,0.26226251211,0.704922999082,0.968316649944,-2.00786030031,-2.90838359324,-2.48132719082,-6.49948001822,9.38966980298,0.176289393573,10.7318308402,-0.35116685483,1.62321790253,-2.92792350482,-0.487020017625,-0.134328304686,-0.860879186319,0.271822695086,-0.234675655352,0.383189888269,-2.04177527532,-0.12566831679,-2.07586094606,-0.170075157391,-0.122866466685,0.846863723976,0.930592757522,1.94634447494,0.862809207421,0.797390167955,0.98130330434,-0.424936054935,0.481031628178,-0.374836182276,-0.110149458012,-0.0794784562337,-0.219477088686,-0.153653554516,-0.233206347529,-0.171659631166,0.094871126241,-0.140546112803,0.218093722,0.104088257355,0.254497721815,0.51432334302,1.28126221362,0.810364564702,0.581606240059,0.160091841165,-0.290946341651,-0.415102558866,0.0513610002819,-0.188071664277,0.194621830847],[-35979.5152944,-375.033352456,9.3128126621,-1858.48761764,-788.770432246,1779.94483311,973.712573543,488.661669314,-970.732724484,268.580436843,720.34659649,-71.511390307,-792.652154908,-748.028204184,-189.374871821,71.2626095919,-196.081392754,24.3549993866,-656.7052473,-413.75865529,-149.194722955,-105.455057564,117.841428905,-450.920474506,149.431787671,38.0067476502,-111.423495768,132.302805303,-51.4537087659,196.143658142,-91.6542288274,-189.9225692,-4.90838745098,-11.1427831646,230.518001466,21.0348143319,19.3753686468,51.7717338543,10.8001405897,-43.4752756421,-56.8471002278,-64.7730020628,-93.3315389307,-19.2027371986,-24.9440459737,22.2404130049,-18.8524100549,-31.8220482738,1.48942514638,7.05185938407,6.54251037338,-1.92122558301,-14.9499819501,-12.2513078035,-18.8821627351,3.61516694727,-25.6321740548,-15.5666826132,-1.1572596083,1.1703830781,16.5408813523,12.3483319078,19.9390603901,-0.539020321316,0.841356494339,-2.09794120194,0.182758559269,0.814907888758,0.951336097703,-1.9731693305,-2.85534573,-2.3609329832,-6.42586240019,9.53451165595,0.164962924899,10.7284766977,-0.326044342298,1.58486478492,-2.9750592084,-0.510466704042,-0.146567516404,-0.866286736996,0.242258251782,-0.276554622974,0.396550142139,-2.06761053724,-0.0922589467844,-2.10070785708,-0.11956470209,-0.0768673534654,0.893808520548,0.929396614864,1.95561852799,0.866410721806,0.804889535956,0.983314411455,-0.439671746804,0.483103274273,-0.372735277319,-0.114087440009,-0.0759245510452,-0.227768244999,-0.168540910222,-0.237860160669,-0.179209199301,0.103012093528,-0.14759955488,0.233295264603,0.111824511855,0.274158100769,0.517106572126,1.2944337256,0.814255950194,0.592950503854,0.16450052298,-0.294146817174,-0.413914089704,0.0494357109315,-0.184017482089,0.19590484029],[-35933.5294854,-362.940214034,27.3699667425,-1832.90106787,-766.348742841,1804.42263416,978.243489586,477.430102281,-994.78724491,267.11305683,698.993850506,-67.1474582471,-786.600838418,-743.581076677,-205.281428244,76.8075775382,-203.70642172,23.377978018,-664.322766257,-406.509279466,-145.552022658,-104.147304908,111.398803007,-446.020686601,152.932171405,35.3301557893,-110.452115916,134.372358768,-51.1465156449,199.177334524,-90.3978369582,-190.477930447,-1.42973284272,-12.1993751718,233.043696876,22.6590704795,19.5316097788,53.1389033614,11.3784806683,-43.0449520546,-56.9430922637,-64.8657250124,-92.4743559707,-17.4382610142,-25.6736993462,22.9173317361,-18.5196809098,-32.8182442254,1.69804994811,7.2385036359,6.55775532736,-1.83870857342,-14.6953766567,-12.2346181021,-18.8236790602,4.14641228561,-25.3417495029,-15.5910004616,-1.0972663317,1.17787003314,16.2698839651,12.4853343851,19.7930102941,-0.540222307992,0.833212739726,-2.15194504128,0.0950348943056,0.942299708087,0.931560798088,-1.92502632684,-2.7877805698,-2.23970328746,-6.35201622876,9.66855330269,0.155140660758,10.7068365191,-0.292973203988,1.52460150463,-3.02884211223,-0.540754294572,-0.157427992906,-0.872005830922,0.20974155972,-0.320738034905,0.410709823254,-2.09507250513,-0.0558043039467,-2.12524395037,-0.0675516394101,-0.0285182983486,0.939640200654,0.926663842865,1.95930691823,0.872198980407,0.805147572677,0.985403272963,-0.458181095949,0.486816748008,-0.370676487239,-0.117633311612,-0.0719106212821,-0.236221911953,-0.184340757753,-0.244012657873,-0.187619996047,0.110962897067,-0.154926188034,0.248334122907,0.119968256609,0.294766220665,0.51982842952,1.3073346494,0.81939432218,0.603510280025,0.169235544236,-0.299023244178,-0.411976673628,0.0470481188753,-0.17951254475,0.197246624414],[-35884.8781675,-368.368379834,38.1496919617,-1808.73191242,-745.100380015,1825.46350663,975.834839274,464.570569991,-1020.93237566,265.585041331,676.841600477,-61.9968620528,-781.847414727,-739.058944351,-221.332033048,82.0677025589,-210.702035017,21.8328976034,-671.826311295,-399.598093779,-140.603049542,-102.609667731,105.101394222,-442.009803262,156.403877732,32.6024747892,-109.202609948,136.660669507,-50.779021999,202.576558142,-89.0279697958,-191.018830152,1.61929611719,-13.7549734773,235.426789075,24.3799014631,19.6405116783,54.6452408115,12.0188978087,-42.4045293375,-56.9914680256,-64.8902783098,-91.5328272912,-15.6357328323,-26.5817554524,23.4022682728,-18.1339956403,-33.9044770409,1.89249943698,7.40199879917,6.5761136051,-1.76487721202,-14.3846337801,-12.180858709,-18.7238267718,4.73957036616,-25.0517236471,-15.6337877252,-1.11383528748,1.18149290144,15.9605958642,12.6330284249,19.6100868914,-0.53993126479,0.814294333922,-2.20385397435,-0.00111546411605,1.08792766123,0.909824948865,-1.86131892794,-2.70444164957,-2.11744103741,-6.27699172275,9.7890900787,0.147917695546,10.6629621382,-0.251580872637,1.44127587743,-3.08712319318,-0.577738857181,-0.166613872429,-0.878390756046,0.174168687895,-0.367184499281,0.425799362187,-2.12414064095,-0.0159028468453,-2.14856250841,-0.0137514676826,0.0222331331677,0.98385786891,0.922921949003,1.95641192657,0.880764684824,0.797174825966,0.988541867947,-0.480746778187,0.492339617498,-0.369002744445,-0.120608727776,-0.0674298467973,-0.244910582586,-0.201031498015,-0.251668108809,-0.196952039713,0.118682583666,-0.162443356917,0.263305070815,0.128503816681,0.316225979846,0.522549213503,1.31973013065,0.825950900785,0.612873447144,0.174584607649,-0.305671122906,-0.409108028859,0.0441514208029,-0.174578874565,0.198648515248],[-35834.9118711,-387.784449209,41.5435842995,-1786.16305008,-724.175750925,1842.52243699,966.61140805,450.61334168,-1048.99112824,264.024251241,653.791401943,-56.3118315931,-778.2511695,-734.718919829,-236.945156175,87.1195535825,-217.264415033,19.7361167676,-679.07610673,-393.153070722,-134.387950265,-100.795933726,98.9626045573,-439.064914868,159.86242866,29.8182922093,-107.683872425,139.142370866,-50.4114125287,206.312376825,-87.5870869843,-191.552950424,4.21608663463,-15.7872014035,237.626073799,26.1936354027,19.7095003192,56.2903850148,12.7022506709,-41.5744515834,-56.9839202947,-64.8635515811,-90.5132092788,-13.8131304052,-27.6653045145,23.6821770755,-17.7095099561,-35.0833510376,2.0715961532,7.54648117734,6.60199256474,-1.70421232248,-14.0149378512,-12.0896421857,-18.5880339624,5.39301546356,-24.7651785579,-15.6937831889,-1.20761372669,1.18049578806,15.6085446743,12.7903454833,19.3915745517,-0.539132162343,0.785153531662,-2.25260640838,-0.105529338559,1.25269356848,0.886423111978,-1.78170738091,-2.60409910783,-1.99511265995,-6.19949508573,9.89412720987,0.143487080541,10.5948554567,-0.202671978678,1.33488221631,-3.14824813608,-0.621030641344,-0.174145798465,-0.885559979833,0.135567982112,-0.415571243011,0.442284596587,-2.15479577252,0.0277517633502,-2.16986526603,0.041593259374,0.0755825609602,1.02581429916,0.918641176394,1.94642621079,0.892274234801,0.780442638839,0.993288478524,-0.507521589873,0.499622743146,-0.367992713304,-0.122943207068,-0.062524971652,-0.253899106333,-0.218497821428,-0.260710111804,-0.207221473621,0.126247173322,-0.170096011284,0.278234753892,0.137466254478,0.338312902752,0.52538330334,1.33139352737,0.833987203792,0.620750060251,0.180694599746,-0.314113262145,-0.405229927415,0.0407057204519,-0.169251739861,0.200077998008],[-35783.8469556,-414.912713376,40.9045109229,-1765.64324453,-701.609318331,1856.02714538,952.002533477,436.692226121,-1078.85430465,262.582717886,629.94306614,-49.9554719263,-775.280992857,-730.670733298,-251.443866679,91.9571692377,-223.681808102,17.1404496149,-685.900536252,-387.193495458,-126.914412502,-98.6360442175,92.9900554166,-437.360925771,163.308389435,26.9317978475,-105.908464788,141.786398291,-50.096967969,210.371010557,-86.1005782208,-192.0732494,6.3560644755,-18.2505834709,239.622566585,28.0981652315,19.7388268957,58.0676950847,13.4018227512,-40.5793516511,-56.9110348917,-64.7980438133,-89.4161470722,-11.9816026954,-28.9133175503,23.7560987072,-17.2605638312,-36.3536317326,2.23709454006,7.67566047648,6.6387490981,-1.66371668657,-13.5854751118,-11.9613875912,-18.4224274133,6.10558316129,-24.4838794297,-15.7672708191,-1.37584832316,1.17537326127,15.2115643941,12.9564656797,19.1390574614,-0.538132874239,0.746999411384,-2.29743663232,-0.218349746397,1.4370473323,0.861326602308,-1.68648173526,-2.48574325737,-1.87335404264,-6.11766500006,9.98268481536,0.142325999015,10.5016874463,-0.147161995349,1.20602245692,-3.21061607851,-0.670038718061,-0.180027899461,-0.893384817477,0.0940670912058,-0.465593127598,0.46060556264,-2.18715488093,0.0753753076088,-2.18848467637,0.0982244550331,0.131757882446,1.06497484146,0.914374410679,1.92914960169,0.906839496592,0.754700191314,1.00015922322,-0.538584782908,0.508544192585,-0.367903092311,-0.124592188919,-0.0571875364086,-0.26321935759,-0.23658904062,-0.270971119131,-0.218476811878,0.13375570105,-0.177863957527,0.293123820628,0.146878833098,0.360798658199,0.528499774815,1.34215107956,0.843575273911,0.626921009124,0.187707552539,-0.324317455351,-0.400298841268,0.036708085468,-0.163557745035,0.201503962577],[-35732.7651073,-445.049424505,41.3256432387,-1747.50039551,-675.83930285,1866.93491135,933.708015996,424.164021164,-1110.33660436,261.432906809,605.586609739,-42.6633936558,-772.236429487,-726.994997513,-264.283658255,96.5373811466,-230.267449361,14.1526151388,-692.159413953,-381.662891632,-118.215384034,-96.0654177335,87.2150659005,-437.086690422,166.730012443,23.8791098996,-103.881192793,144.551783639,-49.875117727,214.746650966,-84.5809361421,-192.554508084,8.030372108,-21.0723354821,241.40269538,30.0891326996,19.7239620598,59.9677582891,14.0883105202,-39.4454835694,-56.7616130054,-64.7009209768,-88.2351629731,-10.1491013431,-30.302262308,23.630301781,-16.7986559538,-37.7100555066,2.3920444879,7.79276917512,6.68836574047,-1.65126852552,-13.0962940502,-11.7962132033,-18.2324625854,6.87741075036,-24.2082142572,-15.8474715173,-1.614111927,1.16788685103,14.7696339387,13.1310820428,18.8547409607,-0.53673546052,0.701261460326,-2.33808120495,-0.339883834212,1.64119911486,0.834488484841,-1.57610777525,-2.34847744498,-1.75218788384,-6.02898470911,10.0547595374,0.145419522395,10.3837338131,-0.085585110675,1.05574570042,-3.27255279367,-0.723939944994,-0.184180360656,-0.901641683123,0.0498238008683,-0.517029638118,0.481126417099,-2.22148517371,0.127106693403,-2.20387221283,0.156054799932,0.191047143744,1.10103612274,0.910816291525,1.90470748001,0.924604920885,0.719972714129,1.00970089047,-0.573881486182,0.518957016601,-0.368904398446,-0.125504777603,-0.0513638631834,-0.27288256479,-0.255157633899,-0.282280258038,-0.230816403624,0.141312376155,-0.185773945177,0.307995236769,0.156738813743,0.383505608316,0.532112411644,1.35192181512,0.854820557106,0.631256608667,0.195808514075,-0.336203810942,-0.394278770641,0.0321913049493,-0.157526936572,0.202892058494],[-35682.349927,-478.744600099,46.0440796843,-1730.86328386,-646.503484239,1876.28303817,912.826761776,414.262049097,-1142.83915156,260.873920367,581.154403732,-34.5705125088,-768.441476753,-724.248122131,-275.070666207,100.8577342,-237.247697667,10.9347572553,-697.818883621,-376.473901767,-108.467792384,-93.049716141,81.6536014684,-438.499013598,170.102033835,20.6219944553,-101.59003142,147.400439096,-49.7720311214,219.403062055,-83.0456615512,-192.994770581,9.21132041416,-24.1691781272,242.957841146,32.1527916472,19.6647464354,61.980497568,14.7414867966,-38.2011837799,-56.5275618051,-64.5768764223,-86.9692162096,-8.32856840864,-31.8048114975,23.3065607096,-16.3387069219,-39.1498793492,2.53842413035,7.9005388424,6.751077688,-1.6719121833,-12.5477698192,-11.5922243067,-18.0232203803,7.70794378095,-23.9398500998,-15.9284428493,-1.91941848763,1.15857782542,14.2834815782,13.3144389531,18.5413764767,-0.534692958308,0.64873247278,-2.37492969713,-0.469877330034,1.86524235453,0.806861774806,-1.45115558347,-2.19173778749,-1.63131965436,-5.93128418883,10.1103891926,0.153298341787,10.2413411687,-0.0188444848791,0.884880598506,-3.33256880471,-0.781808582508,-0.186435372681,-0.910298304177,0.00298018123657,-0.569756262396,0.504131039098,-2.2579494666,0.183054769059,-2.21543726687,0.215222481769,0.25366503934,1.13369345254,0.908497023772,1.87319795887,0.945586138661,0.676292758052,1.02256203296,-0.613349566321,0.530740445211,-0.371185297899,-0.125585314759,-0.0450030204698,-0.282885458614,-0.274129292555,-0.294474258683,-0.244338911646,0.149039716794,-0.193823182201,0.322920020557,0.167030937587,0.40627644935,0.536434227651,1.3606515994,0.867811412547,0.633621138026,0.205187263988,-0.349717395742,-0.387169190451,0.0272044414888,-0.151207164261,0.204220283028],[-35632.8691871,-515.567745623,55.0269710615,-1714.93194233,-613.396862786,1884.92882088,890.865287222,408.165551256,-1175.75922911,261.195191191,557.113348796,-25.9073963176,-763.306677963,-723.275887912,-283.510354479,104.888215211,-244.875850361,7.66888981791,-702.918278032,-371.542578578,-97.9159502304,-89.5897575166,76.3447167532,-441.913084256,173.390528628,17.1068459536,-99.0112442156,150.281214566,-49.8126317812,224.284238972,-81.5304377994,-193.395204686,9.8472519135,-27.4448269444,244.283185606,34.271377935,19.5591921569,64.0932346533,15.34113319,-36.8790638384,-56.2047715259,-64.4333760529,-85.6172207231,-6.54164027369,-33.3865822329,22.7807581731,-15.8975799103,-40.6730430105,2.67927018889,8.00150659709,6.82571602452,-1.73055803244,-11.941155753,-11.3474200356,-17.8005931143,8.59628277024,-23.6832171982,-16.003390595,-2.29094614096,1.14792314202,13.7543522633,13.5077414982,18.2017795706,-0.531264524283,0.590262456561,-2.40884240341,-0.607805745118,2.10918567445,0.779649553115,-1.31258352962,-2.01554672376,-1.51067457194,-5.82238884442,10.149109977,0.166557483675,10.0747053698,0.0521296337887,0.693960296691,-3.38925995705,-0.842707889559,-0.186549600328,-0.91926536244,-0.0462824900081,-0.623639883778,0.529864609691,-2.29672335122,0.243264757882,-2.22270545853,0.275932089222,0.319776812963,1.16246225074,0.907942929108,1.83458030195,0.96985316328,0.623666112806,1.03955252072,-0.656915715048,0.543814539063,-0.374952316131,-0.124726338155,-0.0380242749945,-0.293204022969,-0.293438447922,-0.307371239093,-0.259147381227,0.157087399693,-0.202023406735,0.337983228217,0.177708812598,0.428918657792,0.541703451211,1.36825449713,0.882670501755,0.633856699218,0.216066190412,-0.364813727916,-0.378993560755,0.0218210066953,-0.144653060828,0.20548721737],[-35584.7838848,-553.119618562,64.4217157964,-1699.44311722,-576.393092462,1892.76482331,870.079119103,406.910159672,-1208.50899187,262.540129717,533.881329814,-16.7157368767,-756.294512667,-724.956903508,-289.430746693,108.565543831,-253.462386172,4.54313102176,-707.547682507,-366.823607636,-86.8499305214,-85.7359230519,71.3441646316,-447.653262948,176.558995176,13.2563523192,-96.1151927458,153.11871137,-50.0355248061,229.333985865,-80.0862695603,-193.740189183,9.86223910056,-30.7844123935,245.370252183,36.4256756533,19.4018646033,66.2896815638,15.8628617312,-35.5153823357,-55.7894478449,-64.2820976585,-84.1752105167,-4.81951927836,-35.0050648244,22.0473580129,-15.4935182267,-42.2773927814,2.81851031341,8.09817108632,6.9102306592,-1.83279797172,-11.2793250402,-11.0597500806,-17.5717441665,9.54206364636,-23.4455865659,-16.0634927648,-2.7295955401,1.13584427445,13.1842720505,13.7125619515,17.8385068246,-0.525113369709,0.527218928895,-2.44102860222,-0.752878748524,2.37302204145,0.754066347491,-1.16176327303,-1.82022180482,-1.39060213418,-5.70006723404,10.1700297207,0.185813476712,9.884356717,0.126684384616,0.483467596752,-3.44118213984,-0.905777969077,-0.184182392224,-0.928306889983,-0.0976809224313,-0.678478463837,0.55856133714,-2.33802813389,0.307684967143,-2.22536461237,0.338379756763,0.38949844772,1.18669326981,0.909734176365,1.78877591065,0.99752082763,0.562097185998,1.06152578104,-0.704486252855,0.558093382923,-0.380361810541,-0.12281244839,-0.0303211609836,-0.303780906496,-0.312989793357,-0.320773618598,-0.275364412678,0.165626654624,-0.210404022423,0.353271880388,0.188704640502,0.451189780101,0.548187852162,1.37461772533,0.899541803076,0.63181338487,0.228705079771,-0.381445671022,-0.369786809875,0.0161350561565,-0.137925567782,0.206689997308],[-35536.5346539,-587.218790069,66.7824847666,-1684.02008144,-535.173157521,1898.88184675,853.921240415,411.560968054,-1240.4409242,265.047911414,511.909910349,-6.72157737065,-746.900651405,-730.142477657,-292.709970536,111.81686443,-263.323816807,1.76756496591,-711.800979429,-362.268222002,-75.5651340845,-81.5311754868,66.7244577233,-456.035223214,179.564065679,8.97673504427,-92.863172359,155.823925257,-50.4811325808,234.508554251,-78.764510505,-193.999647107,9.17313116296,-34.0583148085,246.217211816,38.593342303,19.1850379133,68.5501108917,16.2797603043,-34.147465182,-55.2770814057,-64.1330499143,-82.6369789546,-3.19595576656,-36.6102191824,21.1033837761,-15.1473576579,-43.9575170241,2.96067941394,8.19296201847,7.00123411702,-1.98499861491,-10.5667604228,-10.7269406063,-17.3437946496,10.5452553187,-23.2351372428,-16.0985369452,-3.23603446975,1.12120977597,12.5774456719,13.930705968,17.4542429895,-0.514309267014,0.461393454917,-2.47306781479,-0.904044581939,2.65654501587,0.731308566108,-1.00048040963,-1.606496049,-1.27145242919,-5.56221186472,10.1725142412,0.211453107875,9.67174205789,0.204038034575,0.25400317326,-3.48696324844,-0.97022588851,-0.178927290787,-0.937010682982,-0.150844335991,-0.733959813245,0.590365050058,-2.38211779675,0.376121192322,-2.22328694721,0.402802783383,0.462823249399,1.20570551843,0.914365982468,1.73582419101,1.02859549755,0.491689849734,1.08933485782,-0.755935112216,0.573498810629,-0.387540559835,-0.119731519752,-0.021762318796,-0.314519769232,-0.332642387407,-0.334477678486,-0.293119003188,0.174830627421,-0.218996455009,0.368855510572,0.199913477067,0.472818281158,0.556147267684,1.37964977835,0.91853183298,0.627381963083,0.243356424232,-0.399561294868,-0.359615454628,0.0102643813273,-0.131097496954,0.207830935628],[-35486.8622763,-613.223963717,54.4497247814,-1668.62297693,-490.322648907,1901.92154521,845.761443745,423.454817943,-1270.92152345,268.529524648,491.6902477,4.42784331749,-734.621472987,-739.371732342,-293.344377641,114.618252536,-274.77214738,-0.451785156766,-715.826256811,-357.825877747,-64.343181646,-76.9984637827,62.5663135534,-467.254844527,182.385893395,4.1878124241,-89.2203576594,158.282551375,-51.1789610619,239.774704105,-77.6117735989,-194.127386461,7.69906461899,-37.1368158595,246.817623695,40.7572100812,18.9051005907,70.8537397452,16.563519697,-32.8082726874,-54.6674353166,-63.9944803633,-80.9964382606,-1.70586302863,-38.1477834737,19.9522798758,-14.8775636343,-45.7032422019,3.1105002401,8.29020824645,7.0947924663,-2.19264817951,-9.8091849624,-10.3491098732,-17.1230548146,11.6052097938,-23.0604519248,-16.0976959897,-3.81069469153,1.10213008245,11.9391554462,14.1630527769,17.0523315696,-0.496908117248,0.395462538908,-2.50669248674,-1.05970567479,2.95913919112,0.712023063423,-0.830425602259,-1.3757244448,-1.15378451242,-5.40711658515,10.1561416307,0.243950097184,9.43926202743,0.283764074317,0.00674038891001,-3.52520778545,-1.03547161373,-0.17050188397,-0.94480002583,-0.205366191394,-0.789556737826,0.625333513129,-2.42923649965,0.448287258301,-2.21661346528,0.46941435576,0.539592046682,1.2188774874,0.922347822357,1.67593471929,1.06302116275,0.412773898962,1.12365170636,-0.811021407605,0.589940233945,-0.396520241379,-0.115446215362,-0.0122345951324,-0.325310945308,-0.352176492963,-0.348301685012,-0.312486351656,0.184860544078,-0.227850985301,0.384815318922,0.21120910063,0.493535312979,0.565814227611,1.38329720486,0.939712406109,0.620538613538,0.260255105307,-0.419074649335,-0.348552558297,0.0043168915984,-0.124248506292,0.208896703303],[-35436.5232013,-628.374911103,25.8338830441,-1654.76598498,-443.606212367,1900.6102337,846.757646634,442.311439447,-1299.82501105,272.605401124,473.311222666,16.8947459268,-719.396488065,-752.300408599,-291.810887912,116.928038464,-288.003820789,-2.070556606,-719.769556438,-353.51691397,-53.3179416377,-72.2464086789,58.9113503757,-481.213095436,185.041130067,-1.14791959331,-85.2009036942,160.400031561,-52.1325050885,245.127150681,-76.6772978895,-194.062531948,5.40298533849,-39.9222914337,247.134608164,42.9135311167,18.5566767891,73.1836818514,16.696554235,-31.5176087995,-53.9651613549,-63.8750738834,-79.2494939557,-0.378725579995,-39.5740272657,18.6017989822,-14.6915063445,-47.502497567,3.2728395621,8.39256983629,7.19008768684,-2.45791809016,-9.01325759648,-9.93180479352,-16.9145534777,12.7205978095,-22.9306028837,-16.0525901507,-4.45456760388,1.07781604892,11.2718076845,14.4087847106,16.6379041002,-0.471550925798,0.332075032516,-2.54279896509,-1.21876267327,3.27915530194,0.695787628529,-0.653018396689,-1.12947244303,-1.0395222768,-5.23388248601,10.1203707695,0.284405786784,9.18944242384,0.366456645751,-0.255576942798,-3.55469723881,-1.10128523204,-0.158857429936,-0.951150665656,-0.26075309205,-0.844964340656,0.663304816884,-2.47954646747,0.523718538597,-2.20568995942,0.537938496768,0.619700130582,1.22580598708,0.934325190454,1.60941765592,1.10078149266,0.326129267296,1.16454994881,-0.869358155926,0.607293842332,-0.407213252507,-0.11001821546,-0.00164124653763,-0.33609470006,-0.37139277698,-0.362129438293,-0.333424413948,0.195794932722,-0.237012201853,0.401220608442,0.222564520518,0.51311694908,0.577348837714,1.38554567702,0.963099908994,0.611391232424,0.279519082312,-0.439856457944,-0.336626568723,-0.00168660588488,-0.117445070974,0.209842660572],[-35386.8031405,-633.992279626,-11.9731048911,-1644.7597865,-397.700008258,1895.14079945,855.373153102,466.37764015,-1327.44943073,276.933602014,456.383438147,30.3022593362,-701.547605687,-768.046437319,-288.774161776,118.699364717,-303.017998249,-3.26361787097,-723.773580426,-349.348735071,-42.4609469013,-67.3958717968,55.7462699433,-497.51858211,187.572448658,-7.00668235042,-80.880980788,162.13529312,-53.2948388202,250.569949201,-75.9902442131,-193.764205145,2.33621395567,-42.3713265875,247.125782781,45.0669539576,18.1371855703,75.5259968184,16.6795075833,-30.2815409827,-53.181620755,-63.7779887823,-77.398634946,0.774906912964,-40.866940288,17.0626942185,-14.5883940668,-49.3477106537,3.45229770993,8.50032298672,7.28982780521,-2.777944169,-8.18656035156,-9.48518787312,-16.7204733097,13.8879627736,-22.8523096233,-15.9611899166,-5.16666562671,1.04845510769,10.5756332425,14.665697188,16.2183038667,-0.437797188178,0.27297793022,-2.5809640573,-1.38058353683,3.61352673964,0.68161122626,-0.469653902167,-0.869520342634,-0.931494411972,-5.04308101562,10.0651395774,0.333824913093,8.92463443848,0.45273581922,-0.528589639897,-3.57482475785,-1.16759216162,-0.144245112222,-0.955767704117,-0.316374874676,-0.900133042336,0.703795591764,-2.53293832645,0.601725200841,-2.19085109198,0.607539648502,0.703063531192,1.22644561752,0.950693926376,1.53678873521,1.14173047537,0.233150823125,1.2115270619,-0.930401541122,0.625434936538,-0.419543265933,-0.103594024276,0.0100776122672,-0.346870627133,-0.390163698702,-0.375887705027,-0.355723637562,0.207591765217,-0.246446724597,0.418067300698,0.234067106251,0.531415541906,0.590746342691,1.3864575683,0.988583003941,0.600204226915,0.301049412478,-0.461723614473,-0.323865508323,-0.00780663790236,-0.110735516945,0.210639425835],[-35337.953247,-633.34092178,-53.2818476296,-1639.89782441,-355.378039614,1885.89180893,869.325005342,493.798586267,-1353.93798179,281.213430443,440.287220412,44.0539742113,-681.596752114,-785.857843886,-284.891489578,119.931392914,-319.659180013,-4.27331321105,-727.978067172,-345.323960778,-31.7095511323,-62.5325799774,53.0564696581,-515.66179779,190.028514833,-13.3173085332,-76.3522407509,163.47648561,-54.5973507376,256.099286484,-75.5543097812,-193.216705124,-1.40036761374,-44.4681141802,246.771996167,47.2194215378,17.6512471738,77.8682591858,16.5220735421,-29.1023048636,-52.3310222733,-63.7027402095,-75.451227044,1.75744137669,-42.0129932331,15.3523018251,-14.5663813995,-51.2341017429,3.65184243227,8.61380522338,7.39708133642,-3.14616622807,-7.33810491857,-9.02011540268,-16.5414471234,15.1016906268,-22.8288269821,-15.8250214116,-5.94209512641,1.01307633139,9.85253173256,14.9306421703,15.8017590212,-0.395830285371,0.219590247409,-2.62044010898,-1.54414041776,3.95849598245,0.668707042427,-0.282054778078,-0.598093349215,-0.832184750337,-4.83664445135,9.99132650695,0.392148242369,8.6476096221,0.542464893944,-0.807554373402,-3.58552994474,-1.23436067449,-0.12707380839,-0.958525743398,-0.371536859229,-0.954903228764,0.746244081125,-2.58905134257,0.681427410652,-2.17245076298,0.677184461912,0.789383868392,1.2209841842,0.971388863808,1.4588020793,1.18542527073,0.135544348159,1.26386222505,-0.99345407278,0.644255905515,-0.433418347814,-0.0963702556189,0.0229035518061,-0.357643315051,-0.40836491937,-0.389490160248,-0.3790657542,0.220132567248,-0.256042938988,0.435276725087,0.245810196994,0.548310978975,0.605841446972,1.38614340836,1.01589225555,0.587330133328,0.324601094594,-0.484438660264,-0.310360551322,-0.0141032166367,-0.10417433159,0.211286036383],[-35289.4714052,-634.127314527,-92.6422199921,-1639.48845344,-320.140316274,1873.42363237,884.738251076,523.627828757,-1378.73808052,285.102594947,424.592270443,57.1909776629,-659.763190505,-805.331851327,-280.689689792,120.747054899,-337.583722125,-5.2784260364,-732.553456539,-341.361043188,-21.1651329191,-57.6499556709,50.7352610079,-535.045009906,192.460364072,-19.9427539603,-71.696535325,164.4244912,-55.9482580488,261.66755022,-75.3265768737,-192.442876799,-5.67930430129,-46.2191400845,246.07015909,49.3645604286,17.1170219401,80.1952427729,16.2442491274,-27.9761972371,-51.4307231009,-63.6381224113,-73.4292357662,2.58373683815,-43.0094390951,13.5014183032,-14.6258172239,-53.1527450328,3.87086180355,8.73425281842,7.5135536705,-3.55157451795,-6.47825905193,-8.54644848619,-16.375404855,16.3511216066,-22.8568867623,-15.6501366772,-6.7704509478,0.966937804583,9.10601936246,15.1982802887,15.3958039271,-0.346614287394,0.173138695631,-2.66077044199,-1.70745234644,4.30972924505,0.656958884346,-0.0919694028544,-0.318138845463,-0.742531939616,-4.61850235881,9.90109678655,0.457323720718,8.36195240902,0.634695584557,-1.08756533248,-3.58685884845,-1.30164466879,-0.107898781386,-0.959491677266,-0.425567064773,-1.00889893825,0.790033090778,-2.6471010206,0.76179112349,-2.15084317024,0.745974797154,0.877820066991,1.21004042769,0.995625677038,1.37657208839,1.23094509804,0.0351169911339,1.32056074884,-1.05770503908,0.663538733301,-0.448630609953,-0.0885708077811,0.0366935965258,-0.368389273248,-0.425849131225,-0.402821590738,-0.403039298065,0.233229233495,-0.265600064195,0.452725165246,0.257826679944,0.563756150787,0.622252823457,1.38475962134,1.04451712456,0.573161869102,0.349806950112,-0.507711863077,-0.296261012516,-0.0206164879974,-0.0978169229975,0.211776693742],[-35239.6640901,-639.602061273,-126.00099694,-1643.00162959,-293.618549801,1858.2137535,899.004418851,555.441896577,-1401.39185252,288.449065335,409.015267644,69.2414291476,-636.100301554,-826.046328953,-276.519843767,121.199536113,-356.437014982,-6.41928147321,-737.509716025,-337.305385124,-10.8645445006,-52.6854926691,48.6866134866,-555.040296746,194.890234545,-26.7737987639,-66.9835440087,165.004049615,-57.2520707822,267.253263072,-75.2325445166,-191.457816927,-10.3461618992,-47.6295550299,245.036741002,51.4931760993,16.5421911733,82.4878489149,15.864555984,-26.8979712321,-50.4887176438,-63.5639301581,-71.3495864038,3.28029362192,-43.8541930575,11.5506397204,-14.7689506551,-55.0920361115,4.1095699537,8.8601625306,7.6396517571,-3.98608409773,-5.61908355756,-8.07191279155,-16.218929459,17.6257360692,-22.9277379172,-15.44274341,-7.63615863555,0.904464072522,8.34161799609,15.4627744238,15.0072591028,-0.29037586234,0.134857185032,-2.70155845756,-1.86948816114,4.66240971065,0.645874502223,0.0984032312311,-0.0324059252852,-0.662228107271,-4.39284548376,9.79808999064,0.526528092736,8.07191182299,0.728055800972,-1.36368385575,-3.57897069975,-1.36936154021,-0.0871591494281,-0.958467901592,-0.477805860323,-1.06185687618,0.834502248214,-2.70641704383,0.841557939465,-2.1263608486,0.813122653724,0.967399575895,1.19461709776,1.02233853939,1.29154684895,1.27719829424,-0.0662598749368,1.3805555214,-1.12227657022,0.683019529845,-0.464929680493,-0.0804306172751,0.0513555854916,-0.37905235238,-0.44244147467,-0.415721710407,-0.427304437934,0.246638889272,-0.274921695587,0.470205687745,0.270146892607,0.577760786216,0.639530261349,1.38252260797,1.07384971438,0.558113887513,0.376243996454,-0.531210672147,-0.281751743946,-0.0273472306426,-0.0917172488299,0.212110306499],[-35186.7900783,-649.606881596,-151.774287627,-1650.73473364,-275.801694087,1840.27107112,911.514856147,588.858063101,-1421.74431746,291.231148493,393.32101445,80.240789869,-610.75402769,-847.55300223,-272.671241576,121.260963169,-375.911318276,-7.81938872422,-742.712491436,-332.962787788,-0.730367320096,-47.5812989421,46.8663112911,-575.062971901,197.308816642,-33.7455386544,-62.2673658778,165.255436372,-58.4200600991,272.872579986,-75.1871803833,-190.266138278,-15.2327965847,-48.6933304739,243.703185769,53.5964708825,15.9219355928,84.7263901108,15.3966677473,-25.8618538633,-49.5054241086,-63.4538113819,-69.2212697502,3.87964869254,-44.5413637082,9.54164395436,-14.9991619603,-57.041365886,4.36989346941,8.98773850117,7.77461965334,-4.44551687355,-4.77338429711,-7.60216745768,-16.067778143,18.9159687188,-23.0294968826,-15.2083788185,-8.52119495857,0.820923915747,7.56624532738,15.7191889804,14.6424955472,-0.226402757264,0.106035309916,-2.74232182957,-2.03025227804,5.01158615153,0.634353550381,0.286415267286,0.256533777958,-0.590234439122,-4.1637137461,9.68690978562,0.596815851772,7.78179032709,0.820953541595,-1.6312498847,-3.56217596529,-1.437162307,-0.0651645553056,-0.954949565222,-0.527632474268,-1.11362220084,0.878986884738,-2.76656432675,0.919308772067,-2.09933815503,0.877944525132,1.05709165889,1.17589121883,1.0503458474,1.20525475713,1.32307469094,-0.166754837967,1.44287683478,-1.18625907445,0.702480487635,-0.482070027809,-0.0721943285757,0.0668698608226,-0.389553327064,-0.457945883357,-0.427998510098,-0.451614074304,0.260095591821,-0.283832676518,0.487436232951,0.282792444919,0.590359333646,0.657198260754,1.37966825073,1.1032586518,0.542572388037,0.403478371118,-0.554590851664,-0.26703395575,-0.0342473226486,-0.085933206652,0.212304488817],[-35130.4734148,-661.806546462,-169.376933203,-1664.03872549,-265.696236475,1819.31935719,922.967066216,623.620569286,-1440.02681925,293.442946463,377.375598949,90.4785159655,-583.926877531,-869.414917974,-269.411877249,120.824058343,-395.758731443,-9.55359835907,-747.949588193,-328.085519626,9.37909233689,-42.286418687,45.2669088664,-594.585579133,199.672254433,-40.8310217673,-57.5849526853,165.222353261,-59.3592189664,278.562205997,-75.0973355663,-188.868216913,-20.1737074471,-49.3966149769,242.105803527,55.6658204017,15.2379729949,86.8922982553,14.8486450369,-24.8583801123,-48.4790844663,-63.2743218871,-67.0499238971,4.41607872689,-45.0626562122,7.51328294017,-15.3190995985,-58.9923209307,4.65515188666,9.11046710451,7.91598053918,-4.92916767174,-3.95419817746,-7.14218492455,-15.9160419561,20.2119583397,-23.1478474048,-14.9528021418,-9.40714652447,0.712491903967,6.78671700496,15.9633278034,14.3069309856,-0.152939049566,0.0877917724288,-2.78261476078,-2.19084023284,5.35210640232,0.620525313965,0.469351966235,0.54590652815,-0.52476587227,-3.93539749932,9.57260519504,0.665180377571,7.49549336468,0.911750904654,-1.88616016834,-3.5368874255,-1.50456348802,-0.042011059005,-0.948183918302,-0.574507282926,-1.16417907891,0.922800738923,-2.82737449712,0.993489750553,-2.07019708752,0.939917529088,1.14569777495,1.15514285368,1.07832049576,1.11912856154,1.36746870172,-0.26472344718,1.50663874401,-1.24876362132,0.721751094944,-0.499806730765,-0.0641105999207,0.0832983754498,-0.399795732852,-0.472164152649,-0.439459589098,-0.475811739044,0.273299265568,-0.292190488336,0.504087447464,0.295750609763,0.601614482095,0.674729112089,1.37642061653,1.13209717227,0.5268560652,0.431081731484,-0.57753415554,-0.252312847349,-0.0412442297603,-0.0805222185246,0.212387957323],[-35072.2758093,-672.663060091,-179.234716503,-1684.73097971,-262.154701353,1794.84308324,934.260074835,659.033561568,-1456.73949162,294.923141392,361.196832733,100.128555059,-556.093136064,-891.298035203,-267.188183542,119.740692541,-415.776108512,-11.6168562052,-753.014438326,-322.398587092,19.5973411078,-36.8136583525,43.9119184517,-613.227549822,201.909966092,-48.0218053571,-52.9476700049,164.940886196,-59.9571491689,284.348981983,-74.883292442,-187.266011038,-25.0543515646,-49.7238264896,240.264800718,57.6911919914,14.4650053931,88.9691628426,14.2256583783,-23.8710928074,-47.4133390904,-62.9883661997,-64.842042698,4.9131368935,-45.4066571826,5.49067411042,-15.7268943364,-60.9442811948,4.96942756909,9.22014814115,8.05872420773,-5.4379051818,-3.17417657016,-6.69762945482,-15.7551867545,21.5017953343,-23.2675495187,-14.6821337787,-10.2793787161,0.577162285286,6.00654288527,16.1916644508,14.0038876503,-0.0674488228164,0.0807844107511,-2.82242511563,-2.35298685845,5.67844994603,0.601994706199,0.644930508123,0.832122605588,-0.463161669793,-3.71265862827,9.45952148735,0.728830261809,7.21543731322,0.999032925946,-2.12566288843,-3.50330789892,-1.57132869549,-0.0176186378123,-0.937346491062,-0.618028128751,-1.21361609123,0.965131187043,-2.88877869909,1.0624798023,-2.03952829573,0.998811264908,1.23174013034,1.13367302447,1.10479612568,1.0342459159,1.40940080844,-0.359000329453,1.57116454057,-1.30908481942,0.740730163035,-0.517966690216,-0.0564185415536,0.100750806616,-0.40965512612,-0.484921468214,-0.449937179039,-0.499786118461,0.285891877387,-0.299873055027,0.519828342735,0.308930554802,0.611655882787,0.691512641685,1.37295394612,1.15972482384,0.511124816013,0.458676008517,-0.599837055214,-0.23777794003,-0.048306239997,-0.0755287537545,0.212385142692],[-35012.2687343,-675.107358446,-183.461846738,-1714.49322167,-262.970197988,1766.16090383,946.992139394,693.938502025,-1472.56384431,295.569301771,344.912399193,109.466311779,-527.894600861,-912.825914932,-266.414045554,117.823095999,-435.790922599,-13.9364486646,-757.673200249,-315.606545735,30.1075170333,-31.2175922843,42.8844869689,-630.735966251,203.926295041,-55.3265403164,-48.34786695,164.448173596,-60.0894525414,290.260936294,-74.4778802708,-185.44275302,-29.7984147866,-49.6466493784,238.198602924,59.6630009027,13.5729627482,90.9405401378,13.5311992555,-22.8797374753,-46.3163834038,-62.5566306478,-62.6004495214,5.38700747177,-45.5552624739,3.49047696502,-16.2162640892,-62.9009754212,5.31852520363,9.30773909624,8.19532427928,-5.97414723564,-2.44650602265,-6.2751536416,-15.5754912232,22.7722976777,-23.3730438352,-14.4003554489,-11.1255001344,0.416397350157,5.22831854708,16.4018458491,13.735604306,0.0333558872562,0.0855618115267,-2.86198498367,-2.51873794355,5.98449189686,0.575985288866,0.81080639044,1.11077284908,-0.402238727739,-3.50020109104,9.35163091653,0.785757748046,6.94345110406,1.08170403834,-2.34752314458,-3.46142485039,-1.63720056287,0.00817685994204,-0.921434239745,-0.65784220304,-1.2619654503,1.00508528316,-2.95074349513,1.12451578649,-2.00811983688,1.05451325919,1.313515244,1.11276117203,1.12831780647,0.951545369115,1.44809922139,-0.448618556924,1.63602435212,-1.3665704245,0.759377027697,-0.536438746815,-0.0493875573927,0.119373083142,-0.418964810516,-0.496034302175,-0.459246647975,-0.52342588625,0.297467628276,-0.306773087581,0.534278819524,0.322162883092,0.62063400755,0.706896538522,1.36942097141,1.18553955793,0.495463236124,0.485926932491,-0.621322442111,-0.223616237613,-0.055392937158,-0.0709817221712,0.212335692416],[-34948.1675884,-664.167655775,-184.218559537,-1753.56535169,-265.771878912,1733.28566246,962.57386452,727.65836365,-1488.0362482,295.526856043,328.826966797,118.612620796,-499.866951469,-933.790415626,-267.406914949,114.892967521,-455.531433344,-16.3828663794,-761.711092432,-307.358843436,41.0775867354,-25.5237556917,42.309613146,-646.8992536,205.602388592,-62.73967285,-43.777297933,163.792034375,-59.6149160998,296.31307759,-73.7988341669,-183.378037702,-34.3353927871,-49.1304618934,235.936699845,61.5672891677,12.5283094727,92.7867343264,12.7721503368,-21.8637760819,-45.200078913,-61.9338850986,-60.3275419738,5.85446502381,-45.485543842,1.5287362216,-16.7768901407,-64.8641906142,5.7089452918,9.36264594881,8.3156961548,-6.53970782427,-1.78575974292,-5.88166202633,-15.3662231161,24.0088543881,-23.4477272277,-14.1104856835,-11.9324923921,0.234330972248,4.45742637242,16.5929676454,13.5048528396,0.153368316776,0.102488111752,-2.90155751663,-2.6902300158,6.26335949478,0.539777991023,0.964070008261,1.37676352329,-0.338490125337,-3.30306740411,9.25310080093,0.834520521673,6.68196111564,1.15907157638,-2.54917927398,-3.41123519213,-1.70155098691,0.0356579213236,-0.899257424058,-0.693500762457,-1.30920569026,1.04172740414,-3.01321456002,1.17756201743,-1.97687942542,1.10684034019,1.38907517783,1.09365945003,1.14740504422,0.872076891861,1.4829689995,-0.53242183907,1.70092379501,-1.4203465987,0.777731213719,-0.555033633302,-0.043319788831,0.13935752596,-0.427503112365,-0.505306904659,-0.467160575791,-0.5465969863,0.307567679235,-0.312771797798,0.546978941749,0.335209629344,0.628664931137,0.720176111667,1.36597114074,1.20895367932,0.479991142695,0.512508520161,-0.641735158362,-0.210023205607,-0.0623835429758,-0.066911718412,0.212310878697],[-34876.2739701,-638.781280949,-185.280327573,-1800.10650838,-268.413366321,1696.72461603,981.401632841,759.433537211,-1503.37885882,295.251103201,313.422208599,127.499599952,-472.581454981,-954.116537506,-270.601569707,110.790695855,-474.571641051,-18.7835893232,-764.918889378,-297.295894064,52.6337146404,-19.751426145,42.3554382099,-661.542462147,206.801668316,-70.2283379898,-39.2345779629,163.037034963,-58.3835327568,302.502333363,-72.7499199486,-181.053125968,-38.6061467803,-48.1344706198,233.509728785,63.3837568798,11.2964845607,94.484353909,11.9614120599,-20.8051168272,-44.0778134951,-61.0731701644,-58.0279213376,6.3332891771,-45.1709866048,-0.377416458407,-17.3913764464,-66.8313702318,6.14657229166,9.37302739529,8.40807395068,-7.13461329381,-1.2074980218,-5.52355772739,-15.1168058925,25.1952299032,-23.4740220987,-13.8153455024,-12.6865758836,0.0373526752899,3.70189671056,16.765286914,13.3155376861,0.296534505982,0.131567182118,-2.94133086465,-2.86948923801,6.50770666248,0.491085443164,1.10126401632,1.62460673275,-0.268345768616,-3.12670219915,9.16815474201,0.874153588977,6.43394782972,1.23107078053,-2.7276506532,-3.35261407247,-1.76332618379,0.0651808897671,-0.869598237684,-0.724445738075,-1.35529067266,1.07413744545,-3.07601893803,1.21940935663,-1.94672257669,1.15546719869,1.45627915559,1.07757741682,1.16060644553,0.797009455529,1.51358350659,-0.609075931228,1.76565122102,-1.46928759586,0.795865286957,-0.573404374031,-0.0385275289252,0.16090577069,-0.434999831155,-0.512549325782,-0.473407414151,-0.56912856246,0.31569932178,-0.317726651245,0.557407539845,0.347779747529,0.635824970188,0.73061333099,1.36273281869,1.22939084712,0.464853460315,0.538107445537,-0.660744344253,-0.197192248565,-0.0690831703809,-0.0633629855318,0.212402425776],[-34793.4085404,-604.572242368,-191.59264692,-1850.49418803,-269.832606619,1657.3686546,1002.81639887,787.552257869,-1518.34441503,295.409435189,299.32378332,135.761285134,-446.741088712,-973.927107686,-276.604738427,105.422962336,-492.357042761,-20.9242876319,-767.140912097,-285.061736076,64.8227108262,-13.957597286,43.2342859468,-674.579103272,207.384567099,-77.7229029066,-34.7200467357,162.260710525,-56.2414443613,308.800437,-71.237800196,-178.450864017,-42.5730211692,-46.607473963,230.948644284,65.0861741995,9.85111958512,96.0082378105,11.1199075224,-19.687631244,-42.964477864,-59.9288703468,-55.7108147473,6.83946476648,-44.5842927691,-2.21264487033,-18.0345704733,-68.7948794732,6.63549546682,9.32758588803,8.46001094542,-7.75581214583,-0.726508769187,-5.20590545503,-14.8170611413,26.3137003414,-23.4350266323,-13.5180933857,-13.3745854793,-0.165380452277,2.97176481403,16.9204471748,13.1722991576,0.466151150571,0.172220861993,-2.98155917623,-3.05788640382,6.71039519907,0.428479933092,1.21891819724,1.84865975886,-0.188238447845,-2.9766195462,9.10081469763,0.904297095965,6.20264198492,1.29814461058,-2.87981281516,-3.28542524512,-1.82080208172,0.0970431345024,-0.831465508463,-0.750095281302,-1.40013417908,1.10143686093,-3.13878304781,1.24797384042,-1.9184764388,1.20009411081,1.51294007657,1.065666589,1.16655627101,0.727528601144,1.53971591758,-0.677203551323,1.83008950228,-1.51206275125,0.813848309622,-0.591100595774,-0.0353021852963,0.184171550759,-0.441166444045,-0.517614207672,-0.477703197036,-0.590803164269,0.321398587904,-0.321456554862,0.565065543588,0.359543049381,0.642187957851,0.737491523659,1.35981987485,1.24634128883,0.450202311867,0.562443801237,-0.677970775049,-0.185305844753,-0.0752368793944,-0.0604034285231,0.212724904163],[-34700.2247622,-575.377118109,-207.145683085,-1900.04678634,-270.896279493,1615.80179593,1024.31426511,808.734632675,-1531.99618656,296.516405936,287.119876843,142.639640018,-423.203270758,-993.41613883,-286.086437617,98.8549289001,-508.267472292,-22.565378281,-768.331098986,-270.374349341,77.5347217553,-8.27778251034,45.1144645056,-685.990530612,207.238488447,-85.0987264401,-30.2297515969,161.540433287,-53.0620776996,315.148619801,-69.1933971044,-175.554483716,-46.2270174677,-44.4927912102,228.270988716,66.6464473526,8.18879932678,97.3362154335,10.2777719949,-18.4951387663,-41.8744820937,-58.4644513641,-53.3921547271,7.38380181591,-43.7059557503,-3.96090773723,-18.6771586356,-70.7403432915,7.17594918978,9.21856467952,8.46077397884,-8.39549267082,-0.3542500955,-4.93173182142,-14.4583511934,27.3455321287,-23.3162300442,-13.2224311138,-13.9854143663,-0.363381595924,2.27605351431,17.0597376823,13.078958527,0.663751029843,0.223247342278,-3.02258783465,-3.25541502109,6.86547399163,0.351714270764,1.31426140959,2.04392703103,-0.0948943591272,-2.85786407288,9.05437055046,0.924972047102,5.99110262064,1.36105870675,-3.00250615905,-3.20925911098,-1.87172810326,0.131284129607,-0.784399188895,-0.770039351004,-1.44353175614,1.12290457333,-3.20079566062,1.26171002035,-1.89274634793,1.24056449635,1.55702399279,1.05896072399,1.16408842767,0.664754652415,1.56126770098,-0.735602658492,1.89408203896,-1.54734037366,0.831633939641,-0.607640407666,-0.0338788860652,0.209154759663,-0.445753190207,-0.520425310578,-0.479790541974,-0.611353147205,0.324302289656,-0.323742862665,0.569564415495,0.370181275705,0.647853904638,0.740192407073,1.35731355731,1.2593973449,0.436164902176,0.585290208869,-0.693023504954,-0.174497213393,-0.080588819314,-0.0581040899942,0.213376710764],[-34601.7466581,-567.737465289,-234.44702543,-1944.23298748,-274.312201677,1572.15791134,1042.02787265,819.625803548,-1542.96346311,298.545760755,277.142648097,147.232720935,-402.857687651,-1012.83821013,-299.563983584,91.3459256885,-521.734349034,-23.5342575376,-768.561807442,-253.125311991,90.5093945902,-2.83960629448,48.0558348954,-695.725078128,206.322158536,-92.1874869777,-25.760070562,160.931607154,-48.7838729655,321.465766746,-66.5812941048,-172.372942503,-49.5771958683,-41.762467532,225.478111291,68.0416522012,6.33595240202,98.4550552876,9.46963026598,-17.2167511456,-40.8192919013,-56.6650206424,-51.0964415365,7.97068681089,-42.5337619653,-5.6043761619,-19.2930749254,-72.6500593982,7.76269698126,9.04525414045,8.40383066751,-9.04090719937,-0.0973745990071,-4.70145520537,-14.0360272568,28.273174128,-23.1081242356,-12.9342860476,-14.5111372832,-0.549564810121,1.62109985894,17.1821991029,13.0372695798,0.888199395402,0.283291483585,-3.06468915678,-3.46023038608,6.96944525994,0.261818397758,1.38561199475,2.20679066567,0.0138077444306,-2.77487617202,9.03085108138,0.935852238862,5.8017217458,1.42041774303,-3.09350782835,-3.12360149318,-1.9142080674,0.167506135678,-0.728693474599,-0.784141213526,-1.48506732243,1.13817525892,-3.26101263534,1.25990360465,-1.86983544418,1.27683115996,1.58692676235,1.05821385966,1.15231505885,0.609603538209,1.57810081696,-0.783531679226,1.95731958023,-1.57411557729,0.849097228903,-0.622611604975,-0.0344192806137,0.235612129758,-0.448609578944,-0.520979180165,-0.479493495026,-0.63046808692,0.324228677694,-0.324345679961,0.570706162585,0.379453761775,0.652936286111,0.738268956302,1.3552568233,1.26826515759,0.422811528436,0.606461456602,-0.705619749455,-0.164839485969,-0.084986562036,-0.0565246198727,0.214396217936],[-34504.5463331,-590.604908159,-272.011423521,-1980.57165007,-282.428843974,1526.59364511,1053.21963339,819.068454918,-1550.16144797,300.894068667,269.227568806,148.957017175,-386.218427873,-1032.61155527,-316.825788927,83.2573716462,-532.453230707,-23.8597797709,-767.986156465,-233.421410321,103.41418727,2.4045897941,51.9593712507,-703.617767945,204.684883179,-98.8305180598,-21.3222619156,160.451152293,-43.4587505212,327.670540805,-63.3919721824,-168.974134683,-52.600000872,-38.4507058612,222.583241117,69.2640699754,4.34642579012,99.366070558,8.72576729712,-15.8598278159,-39.8051324668,-54.547333457,-48.8563387082,8.60324230933,-41.0947134953,-7.12281189785,-19.872443058,-74.5095641831,8.3859875802,8.8162314849,8.28945031542,-9.67641131391,0.0428919129586,-4.51220283427,-13.5540143904,29.0840752785,-22.8094197658,-12.663787593,-14.9470955935,-0.724659180312,1.01023094303,17.2838039335,13.0456829517,1.13539536133,0.351248192098,-3.10773837857,-3.66859858958,7.0224741005,0.160954515301,1.43204042365,2.33597057388,0.137654024186,-2.73084776136,9.03083500979,0.935320798941,5.63570443303,1.47532526737,-3.15279896963,-3.02859148429,-1.94739672768,0.204791100425,-0.665504021433,-0.792614907501,-1.52412842212,1.14747458587,-3.31828395029,1.2428818875,-1.84964682406,1.30881763601,1.60192864562,1.06363218412,1.13068410798,0.562579297962,1.58977925233,-0.821013405402,2.01929909011,-1.59213616933,0.866139941372,-0.635899786392,-0.0369823780698,0.263025919145,-0.449735458516,-0.51937362786,-0.476759045741,-0.647853865573,0.321275298199,-0.323055413522,0.568515099949,0.387291983362,0.657507702857,0.731570349239,1.3536577483,1.27278458238,0.41012561108,0.625778980894,-0.715716946896,-0.156351587026,-0.0884624781678,-0.0556930024961,0.215745388731],[-34413.6333505,-640.295031312,-314.11113434,-2009.2394856,-295.588653175,1479.2056477,1057.34750658,808.395125719,-1553.21827051,302.580966916,262.670438224,147.89931096,-373.290765146,-1053.1091401,-336.795474102,74.9340126927,-540.45147065,-23.7802266869,-766.744623908,-211.601895289,115.92038917,7.70671646923,56.5574841645,-709.363314461,202.450739592,-104.909366978,-16.9448777132,160.077202671,-37.2695684633,333.704075997,-59.6387843757,-165.476853275,-55.2255707206,-34.6551213132,219.608884202,70.323039573,2.29143118514,100.086917293,8.06695307722,-14.4528070241,-38.8265289943,-52.1636406316,-46.707487027,9.28270157812,-39.4462070495,-8.49316581251,-20.4235042053,-76.3062295892,9.03248751323,8.54756072836,8.12537385094,-10.2856234405,0.0715664855358,-4.3579164806,-13.0264850413,29.772883602,-22.4274782908,-12.4239756686,-15.291666793,-0.897702756427,0.44340178551,17.357005595,13.0987628253,1.39867489237,0.426053160215,-3.15128551653,-3.87567540684,7.02875128669,0.0517504761749,1.45342165282,2.43306300496,0.273701239572,-2.72689586157,9.05319510808,0.92051271982,5.49300363261,1.5232936647,-3.18273069611,-2.92499701584,-1.97167444658,0.241889859865,-0.596843798084,-0.796114646029,-1.56012058961,1.15166252329,-3.37167686848,1.21206086619,-1.8317435394,1.33635639924,1.60244052544,1.07485369787,1.09923735321,0.523821299436,1.59560068602,-0.848881195728,2.07928954163,-1.6020397516,0.882682497687,-0.64770413639,-0.0414755735315,0.290654829029,-0.449295964562,-0.515837133613,-0.471697794056,-0.663332415444,0.315826101412,-0.319795819035,0.563254691649,0.393817829089,0.661587356416,0.720320391832,1.35249406386,1.2729492175,0.398024764116,0.643087232908,-0.72353440447,-0.148964754732,-0.0912590437954,-0.0555926983449,0.217293228287],[-34332.374995,-702.947981412,-353.996863693,-2032.73838753,-311.981799736,1429.95871312,1056.37593959,790.347755788,-1552.56923615,302.550085956,256.463755738,144.808235804,-363.772733205,-1074.53768831,-357.882953308,66.5967867138,-546.032761919,-23.6620964559,-764.901450835,-188.150678776,127.809305269,13.4464650013,61.5485175124,-712.634749474,199.774407728,-110.370473139,-12.66743834,159.763366628,-30.4853346566,339.543788991,-55.3441401839,-162.009339244,-57.3600121524,-30.5013384166,216.582825776,71.240790591,0.241809264816,100.643978842,7.50222819252,-13.0406051346,-37.8659892498,-49.5873235611,-44.678784088,10.0074867299,-37.6592221313,-9.6958318065,-20.9624049776,-78.0271061191,9.68871081896,8.25838080907,7.92387222811,-10.8544642141,-0.00267497214454,-4.23042295595,-12.4747873608,30.341000228,-21.9751512237,-12.2275468479,-15.5456014726,-1.08075128261,-0.080302965305,17.3935096721,13.1890304651,1.67041783835,0.506793308698,-3.19468156894,-4.07661755786,6.99495042921,-0.0633604625977,1.44990507259,2.50176021665,0.417292721207,-2.76197802047,9.09557960499,0.888415101045,5.37282685553,1.56118590895,-3.18714746493,-2.81405028342,-1.98795248741,0.277485588757,-0.525073823434,-0.795550176427,-1.59259767576,1.15197281267,-3.42063924484,1.16945111581,-1.81551224174,1.35922647501,1.58975864851,1.09117451151,1.05861528783,0.493296585477,1.59492291859,-0.868408274987,2.13654489287,-1.6049778291,0.898676716316,-0.658388829109,-0.0477006512113,0.317697594874,-0.447544173553,-0.510676526879,-0.464521932378,-0.676868673607,0.308422813822,-0.314641392069,0.555328543279,0.399268902926,0.665168801279,0.705037698554,1.35174722884,1.26891657794,0.386421264084,0.658291914902,-0.729437598612,-0.142542476229,-0.09371723711,-0.0561906105176,0.218869001319],[-34263.4356024,-763.223883044,-386.535886273,-2054.08057055,-329.137831253,1379.04948889,1053.27735567,767.513541617,-1549.00692889,299.89543146,249.766602269,140.660217553,-357.354089384,-1096.94530446,-378.560525377,58.3591368167,-549.60664002,-23.8457041802,-762.48408899,-163.557064475,138.979118983,19.9885067792,66.7127783803,-713.23109862,196.799871805,-115.209200948,-8.52729832304,159.455696689,-23.3778050899,345.191938298,-50.5304035208,-158.672743001,-58.9287036794,-26.1004935563,213.53300791,72.0432901346,-1.74206943867,101.063123327,7.03201015623,-11.6700806816,-36.9042280217,-46.8909161851,-42.7880191688,10.7740043119,-35.7970043527,-10.7187003973,-21.5000653938,-79.6593380462,10.3430674527,7.9670856513,7.69672328258,-11.3725393199,-0.169985173831,-4.12214119857,-11.9205249693,30.7934615993,-21.4659510401,-12.0832651053,-15.711573661,-1.28213876399,-0.560552581485,17.3873502507,13.309311112,1.9434459184,0.592691945751,-3.23748106137,-4.26723996311,6.92803899193,-0.182533029276,1.42193599238,2.54600516346,0.563990192424,-2.8335373585,9.15542957745,0.837401087365,5.2744422663,1.58655612027,-3.17005666434,-2.6971680927,-1.99694509215,0.310388629387,-0.452391448013,-0.79187785906,-1.62122657198,1.14956506529,-3.46496616882,1.11713314511,-1.80053397847,1.37739176996,1.56547221495,1.11189195878,1.00992880505,0.471009654917,1.58752840757,-0.880791183109,2.19054593182,-1.6020927986,0.914116980854,-0.668284906953,-0.0554369773923,0.343443197557,-0.444721468741,-0.504199860687,-0.45550556008,-0.688507047787,0.29958872545,-0.307803615828,0.545182782439,0.403843952335,0.668292680727,0.68636997909,1.35145856105,1.26102237118,0.375304433287,0.671400335294,-0.733765399937,-0.136924351824,-0.0961218786652,-0.0574563870355,0.220327693828],[-34207.5455922,-811.86879091,-410.741955271,-2075.42582893,-345.338527912,1327.20347151,1050.76440772,741.928886564,-1543.2745123,294.004806585,242.065768178,136.111128555,-353.822588339,-1120.49111835,-397.605497307,50.3157475881,-551.529606753,-24.5892796245,-759.569090547,-138.240654652,149.384739535,27.6167378723,71.9254090246,-711.136221267,193.655225278,-119.430120075,-4.55148356934,159.1008105,-16.1876917778,350.641012767,-45.226817483,-155.55814334,-59.8893851191,-21.5433548499,210.489188138,72.7536090799,-3.60353637022,101.366241975,6.65563322855,-10.3857476107,-35.9278332465,-44.1392689444,-41.0480878871,11.5758872546,-33.9133246868,-11.5615142784,-22.0416580629,-81.1923473796,10.9850918463,7.69166278024,7.45351520879,-11.8304439076,-0.419952521766,-4.02633178969,-11.382598993,31.1358641207,-20.9133207533,-11.997862066,-15.7939226413,-1.50604840029,-0.995191820057,17.3359023216,13.4536396468,2.21102575707,0.682957198534,-3.27941799162,-4.44334723879,6.83465720831,-0.30409307984,1.37020885115,2.56919456595,0.709986950149,-2.93852711197,9.23017508792,0.767011142809,5.19701331656,1.59755955245,-3.1353619326,-2.57609276065,-1.99890351948,0.339464375242,-0.380796189604,-0.786032222588,-1.64559490289,1.14537356151,-3.50452593677,1.05710795105,-1.78655530377,1.39105466555,1.53114972206,1.13634048812,0.95442121848,0.456964802633,1.57353053398,-0.887033735052,2.24101221736,-1.59437669706,0.929053425494,-0.677665625438,-0.0644812268005,0.367260617819,-0.441041303759,-0.496692274638,-0.444953650342,-0.698279909816,0.289792459418,-0.299551625721,0.533273161195,0.407650623791,0.671037547083,0.664967914213,1.35171195796,1.24969009902,0.36473108861,0.682458637134,-0.736806206312,-0.131965228212,-0.0986605509432,-0.0593754000796,0.221574215893],[-34164.06552,-846.231229195,-427.588632701,-2098.1069107,-360.134601269,1275.56217387,1050.74773243,714.955308643,-1535.89538321,284.478655918,233.138410544,131.428428107,-353.030140002,-1145.39908942,-414.126507292,42.571589218,-552.091789579,-26.0721055672,-756.318374236,-112.570933898,158.982795071,36.4943618902,77.1001416404,-706.507112451,190.453190601,-123.033279808,-0.756419122205,158.642492745,-9.12060172184,355.86534953,-39.4869545936,-152.75066289,-60.2443279144,-16.9033273808,207.478156818,73.3886967229,-5.28716837938,101.571678083,6.37245361553,-9.22592812948,-34.9323536746,-41.3905753052,-39.4722521151,12.4017003526,-32.0539782671,-12.2343278725,-22.5871290566,-82.6183352083,11.6046724684,7.44924289631,7.20232807225,-12.2196469745,-0.741420456627,-3.93770095814,-10.8766312609,31.3735185382,-20.3314046147,-11.9761206939,-15.7995232554,-1.75264426481,-1.38175451305,17.2393126281,13.6168451349,2.46683879193,0.776690776614,-3.32031846382,-4.60060512741,6.72110122581,-0.426301996651,1.29593730297,2.5740912305,0.85202359719,-3.07365149689,9.31706051942,0.678047001882,5.13949289934,1.5930256875,-3.08674469153,-2.45271559154,-1.99373140559,0.363632939864,-0.312130814777,-0.778867169115,-1.66518681584,1.14013272003,-3.53916906243,0.991329500368,-1.77343873582,1.4006059284,1.48826071732,1.16381183326,0.893397458711,0.451025492348,1.5533131351,-0.88801744983,2.28785040348,-1.58268087689,0.943582838558,-0.686742153193,-0.074645443609,0.388582247051,-0.436703271055,-0.488408332555,-0.433180336616,-0.706189142806,0.279461836498,-0.290166658241,0.520054646222,0.410717973359,0.67349087253,0.641460088243,1.35259671711,1.23541410293,0.35479242602,0.691549049512,-0.738805802293,-0.127530189726,-0.101428617781,-0.0619334107964,0.222557151116],[-34131.8501921,-869.047499063,-438.405324592,-2122.8170413,-374.374506057,1225.33879805,1054.03312427,687.27223069,-1527.13306086,271.052037183,223.049454001,126.509536989,-354.896589472,-1171.90100823,-427.592850235,35.2480091749,-551.50934103,-28.3865408474,-752.962718839,-86.8952252017,167.6729197,46.6334084014,82.1589669863,-699.629408341,187.286300871,-126.006597869,2.85335125929,158.018689022,-2.3482100371,360.817963447,-33.401980335,-150.322001816,-60.0473900927,-12.2428574352,204.515268003,73.9574354804,-6.7422064894,101.695101762,6.18339992532,-8.21899025798,-33.9219288571,-38.6991217228,-38.0756490895,13.2305062266,-30.2576598292,-12.7544605037,-23.1308486485,-83.9305015737,12.1912247947,7.25441457935,6.94996766359,-12.5326268544,-1.12265636611,-3.85238371474,-10.4151688707,31.5113167818,-19.7352337837,-12.0200921704,-15.7379898753,-2.01842293949,-1.71857834917,17.0993403665,13.793804516,2.70517942437,0.872669525466,-3.36013504068,-4.73480979335,6.59323710475,-0.547226199564,1.20119099648,2.56296840369,0.987224145449,-3.23532321088,9.41292360474,0.572511762553,5.10060969143,1.57255706257,-3.02766430233,-2.32888322135,-1.98113289389,0.381993172169,-0.24810267537,-0.771139328057,-1.67949959168,1.13443998558,-3.56868975114,0.921706927397,-1.76112761352,1.4065666954,1.43818270507,1.19352434343,0.828271217853,0.452822038045,1.52749573685,-0.884585048076,2.33103605079,-1.56769604802,0.95783246733,-0.69564063558,-0.0857340723654,0.40690911385,-0.431889938429,-0.479589833924,-0.42050230456,-0.712224594445,0.268988824946,-0.279917638816,0.505982354602,0.413038517424,0.675727305567,0.616447389486,1.35416478784,1.21873058964,0.345590326732,0.698779612925,-0.739957751611,-0.12348308489,-0.104451964026,-0.0651086923173,0.223251293417],[-34109.2263426,-883.861744641,-443.742649738,-2149.82991154,-388.776036461,1177.28675948,1060.66065851,658.991816402,-1517.14690042,253.706666288,212.068375595,121.28632448,-359.260133842,-1199.94649977,-437.871083588,28.4032169952,-549.947442907,-31.5491789329,-749.691142245,-61.5389188903,175.324881781,57.9074240508,86.999709077,-690.844770342,184.213763774,-128.340577514,6.27452841209,157.173126907,3.98567740598,365.45255054,-27.0809663819,-148.319290977,-59.3965090364,-7.61047526524,201.598008122,74.4634391255,-7.93277178553,101.749271589,6.08930100664,-7.38306774113,-32.9024031279,-36.1144416389,-36.8723557691,14.0331628498,-28.5558965595,-13.1388799516,-23.6597968434,-85.1202329707,12.7344382255,7.11699348573,6.7022129521,-12.7639382917,-1.55243057993,-3.76734839399,-10.0083618424,31.5547943113,-19.139493181,-12.1285699368,-15.6206774603,-2.29721433343,-2.00608357068,16.9178712844,13.9790328411,2.92144506006,0.969437125157,-3.39890803325,-4.84262353342,6.45627888078,-0.664948534879,1.08882160901,2.5381690679,1.11302563948,-3.41964879131,9.51415082486,0.453309478149,5.07891624796,1.5367355795,-2.96124889615,-2.20612369104,-1.96076189825,0.39399560226,-0.190186079619,-0.763500227341,-1.68823400816,1.12882347661,-3.59289658838,0.850036759534,-1.74959492336,1.4094688094,1.38225075068,1.22464079638,0.760602775815,0.461788918412,1.49686826668,-0.877627555857,2.3704519442,-1.54997971519,0.971889921199,-0.704307481828,-0.0975381551326,0.421852113925,-0.426752620135,-0.470472902626,-0.407232138431,-0.716407287499,0.258714858198,-0.269070077785,0.491493195861,0.414617162417,0.677796817246,0.590510245663,1.35639938422,1.20019420355,0.337206202637,0.704288444744,-0.740414995223,-0.119664857021,-0.107713585036,-0.0688616439285,0.223618194259],[-34093.4809869,-892.848447327,-443.317981996,-2178.76460785,-403.813582977,1131.96962126,1070.43289595,630.526342976,-1506.07974137,232.674671002,200.614979443,115.903744393,-365.864064533,-1229.27585179,-445.097607037,22.0635573463,-547.518544621,-35.5401971848,-746.617791735,-36.789394419,181.813431499,70.1518070053,91.5082326718,-680.49555233,181.270446903,-130.037236231,9.50630949174,156.058767574,9.76954932089,369.732259577,-20.6372470581,-146.776264941,-58.4111459442,-3.05210626097,198.719749963,74.9052445765,-8.83795799351,101.745566569,6.09040497267,-6.73020728519,-31.880000146,-33.6793135257,-35.8730796491,14.7803897876,-26.9722033156,-13.3996362121,-24.1557709463,-86.1781500325,13.2248930136,7.04295554975,6.46388507873,-12.9108693154,-2.01985372749,-3.67996526941,-9.66367452238,31.5105507369,-18.557356268,-12.2981147837,-15.4587709687,-2.58165421993,-2.24529457767,16.6966787558,14.1668563618,3.11212489048,1.06535419246,-3.43652421257,-4.92167074845,6.31484493704,-0.777605506794,0.962063548454,2.50202667074,1.22715566653,-3.62245246733,9.61718384201,0.323969498748,5.07301490584,1.48679372626,-2.89050672938,-2.08579782684,-1.93239909942,0.399385167615,-0.139566402324,-0.756505113552,-1.69125787786,1.12374576815,-3.61163760123,0.77794589105,-1.73876831413,1.40980800438,1.32178943363,1.25629367169,0.691955237938,0.47724773921,1.46225223098,-0.868000400577,2.40589776409,-1.52994732709,0.985845108245,-0.712551737655,-0.109839117939,0.433138941525,-0.421425985734,-0.461278976595,-0.393662608833,-0.718780435883,0.248944908093,-0.257879553891,0.476972802297,0.415473994084,0.679708899823,0.564187666619,1.35922986989,1.18034623582,0.32969572284,0.708219753592,-0.740305506946,-0.115915564147,-0.111164992464,-0.0731358134348,0.223608962931],[-34081.0734812,-896.868257353,-436.439689925,-2208.70700338,-419.401275785,1089.82073302,1082.82471158,602.159155134,-1493.94657285,208.44190904,189.20047112,110.688672947,-374.367566477,-1259.36202752,-449.513555835,16.2439275457,-544.292956129,-40.2919338475,-743.755035491,-12.9107639399,187.039091532,83.1530003361,95.5482155535,-668.929359464,178.470196758,-131.099799137,12.5413728658,154.648691204,14.9179443663,373.626641387,-14.1936587871,-145.709512595,-57.2279139027,1.38708784401,195.871503213,75.2765705116,-9.44867199064,101.69236739,6.18519488411,-6.26541627487,-30.8602635947,-31.4324431116,-35.086093301,15.4422748001,-25.5255414638,-13.5424798198,-24.5982613106,-87.0934271431,13.6536741241,7.03462666851,6.2390534936,-12.9732357574,-2.51431786981,-3.58842581909,-9.38630732144,31.385502275,-18.000248504,-12.5231727326,-15.2621426566,-2.8636232938,-2.43800944942,16.4368958994,14.3512663799,3.27455642839,1.15864885422,-3.47268411837,-4.97064821247,6.17292147811,-0.883431495957,0.824601230133,2.45691140595,1.32768309025,-3.83932054294,9.71858908072,0.188377953217,5.08172092974,1.42433558337,-2.81810887589,-1.96894026359,-1.89603694911,0.398175972891,-0.0972089546975,-0.750571751543,-1.68857510686,1.1196324122,-3.62478608407,0.706960941579,-1.72851436242,1.40796828457,1.25809861342,1.28763110014,0.623849968562,0.498503770184,1.42443784785,-0.856551197577,2.43707861814,-1.50795902679,0.999727322452,-0.720117743505,-0.122416755723,0.440597238364,-0.416029597505,-0.452198372458,-0.380062416731,-0.719402444059,0.239947794668,-0.246577780597,0.462755965779,0.415647149868,0.681431302522,0.537964759938,1.3625437175,1.15967546469,0.323083373136,0.71070293503,-0.739736232394,-0.112080811909,-0.114746464781,-0.0778495072871,0.223160795157],[-34067.6154468,-898.565629114,-424.971091686,-2238.20715817,-435.259374791,1051.04990419,1096.55705562,573.792632741,-1480.54812065,181.692977964,178.328095521,105.844861793,-384.456261615,-1289.58417668,-451.467325683,10.9534727385,-540.274105011,-45.7028371028,-741.071696762,9.8408226471,190.923049372,96.6078329469,98.9726490328,-656.529059176,175.809302301,-131.523099279,15.3638100948,152.938030621,19.3638209962,377.095486126,-7.88473070004,-145.12930476,-55.9986337998,5.66615269681,193.046034726,75.5656696163,-9.76333217602,101.593978226,6.37200375487,-5.98724689741,-29.8494953649,-29.4105947303,-34.5182148758,15.9845180027,-24.2318921447,-13.5723993645,-24.9671709038,-87.8564154835,14.0120642286,7.09095101253,6.03145050291,-12.9518450392,-3.02577192212,-3.49133263491,-9.17939878455,31.1865759092,-17.4792006479,-12.7965530492,-15.0399161871,-3.13458103676,-2.58669950866,16.1395569054,14.5265114487,3.4068050084,1.24734910111,-3.50688080001,-4.98897534332,6.03392164641,-0.980516185002,0.680421477783,2.40543101634,1.41280021711,-4.06577243918,9.81473178522,0.0504083272439,5.10371639006,1.3510137664,-2.74640291088,-1.85645708241,-1.85179816818,0.390636394918,-0.0639320993672,-0.745969133953,-1.68028555995,1.11683451895,-3.63213526285,0.638504892532,-1.71859247656,1.4041899023,1.19248499919,1.31775499174,0.557733280007,0.524838044425,1.38417454534,-0.844138756467,2.46364641161,-1.48436548088,1.01350733161,-0.726707174655,-0.135042633231,0.444135824322,-0.410675075221,-0.44340550163,-0.366681769244,-0.718331280109,0.231938557463,-0.235345751795,0.449138500571,0.415204204049,0.682891254152,0.512269678186,1.36618625613,1.13859556539,0.317358081135,0.711824233783,-0.738799279793,-0.108031400345,-0.118377547896,-0.082903661316,0.222207673339],[-34048.3906797,-902.212811104,-413.583902944,-2265.8315476,-451.279978319,1015.55950338,1109.99237691,545.13638922,-1465.56227582,153.165157359,168.395257241,101.420142632,-395.942027405,-1319.41602322,-451.321453901,6.21997296409,-535.435850279,-51.6865192625,-738.530112196,31.213956845,193.407671646,110.163390827,101.663452076,-643.692451722,173.280525107,-131.300741044,17.9498256631,150.936932179,23.0535836705,380.092540037,-1.85943082835,-145.040638944,-54.8738896661,9.74557666813,190.243902424,75.7582304813,-9.78397040519,101.450647819,6.64827341983,-5.89111318477,-28.8566878532,-27.6490655717,-34.1734897607,16.3727129282,-23.10325005,-13.4948915583,-25.2451515512,-88.4607238384,14.2922452924,7.2091761807,5.8446703139,-12.8485850381,-3.5450392873,-3.38775469873,-9.04452227968,30.9206080098,-17.0053921579,-13.110114557,-14.8002787888,-3.38597324241,-2.69349027213,15.8062111179,14.6875351226,3.50758945579,1.3295866871,-3.53826871052,-4.97642545045,5.90078907837,-1.06690930816,0.533433445478,2.35011782472,1.48065920257,-4.29731009121,9.90218633504,-0.0861289773209,5.13770986472,1.26832301098,-2.67741518444,-1.74927285597,-1.79978903121,0.377153699379,-0.0403587682003,-0.742793981336,-1.66647935054,1.11563440919,-3.63340671194,0.573851032733,-1.70867914619,1.39855749976,1.12623896363,1.34569986366,0.49487246037,0.555504573418,1.34212731164,-0.831521077048,2.48527402516,-1.45942729906,1.0271685714,-0.732055417092,-0.147505504768,0.443732463869,-0.405472727734,-0.43504123422,-0.353730011488,-0.715604128146,0.22509055428,-0.224305981246,0.436352573592,0.414228966528,0.683964088716,0.487459316236,1.36998096468,1.11745251909,0.312496906094,0.711618727081,-0.737551115927,-0.103680068008,-0.121953057565,-0.088197812313,0.220703202835],[-34019.0247608,-910.633175964,-408.14090808,-2290.85408866,-467.007890859,982.858527747,1121.73845559,515.828284245,-1448.73977163,123.565519489,159.720103245,97.5229919206,-408.648843877,-1348.19031536,-449.284638034,2.05137605646,-529.789486935,-58.1583936976,-736.048842331,50.999951615,194.521677406,123.486643433,103.561999185,-630.768594108,170.872066503,-130.443638429,20.2742338415,148.661957716,25.9491733592,382.591997764,3.74123808638,-145.416307074,-53.978550965,13.599883061,187.475714089,75.841106423,-9.51891076384,101.259391347,7.00654347006,-5.96928757899,-27.8892527514,-26.1770713103,-34.045731794,16.5783477764,-22.143693644,-13.3096847124,-25.4184829656,-88.9008618795,14.4885856876,7.38521270246,5.68215947997,-12.6678199782,-4.06417299414,-3.27779091857,-8.98164301149,30.5953281089,-16.5884138421,-13.4538373355,-14.5484882056,-3.60935464851,-2.75947787285,15.4382237156,14.8305507891,3.57651287461,1.40394009113,-3.56584161213,-4.93332813295,5.77585709374,-1.141211161,0.387292492072,2.29340580945,1.5295571223,-4.52931332543,9.97827024661,-0.217492962526,5.18310886288,1.17758886029,-2.61227994204,-1.64812851187,-1.73993980294,0.358216424443,-0.0268061107382,-0.741035372856,-1.6472343111,1.11623137273,-3.62840661451,0.514030103897,-1.69847870238,1.39101744622,1.0605696302,1.37056073249,0.436409158535,0.589982696575,1.29889443515,-0.819159059072,2.50164488494,-1.43323351364,1.04069127195,-0.735941697924,-0.15962784067,0.439452413816,-0.400533876593,-0.427184992763,-0.341369173526,-0.71126588568,0.219523042362,-0.213574316495,0.424557715122,0.412799944904,0.684486291307,0.463822926268,1.37377933726,1.09653886462,0.308515739712,0.710085485683,-0.735970665417,-0.0989673346986,-0.125349314547,-0.0936326394134,0.218602866736],[-33975.8496999,-925.799507413,-415.320583828,-2313.81126071,-481.967703147,952.452395038,1130.6456218,485.991895361,-1429.99486868,93.5062416547,152.602527329,94.1379088834,-422.291501445,-1375.30119761,-445.330605429,-1.55408865206,-523.412082245,-65.0396354639,-733.508002831,69.074513661,194.384305565,136.305620003,104.678636053,-618.058062558,168.575225556,-128.989922356,22.3156988665,146.133516712,28.0308066882,384.581565516,8.79270011905,-146.205993022,-53.3992686565,17.2217675171,184.762225587,75.8043047343,-8.98294821699,101.012901061,7.43415537458,-6.21315536863,-26.9530828146,-25.0142370935,-34.1189646505,16.5794991587,-21.3482061411,-13.0160620569,-25.4810326416,-89.1761655845,14.5983729743,7.61409772447,5.54697177412,-12.4167171702,-4.57688319374,-3.16230855595,-8.98876378124,30.2190962119,-16.2358124402,-13.816712974,-14.2863215528,-3.79724415346,-2.78480773062,15.0374863315,14.9538092251,3.6141928097,1.46962801171,-3.58848840401,-4.86059632445,5.66081055886,-1.20273944038,0.245286339826,2.23741731763,1.55810916969,-4.75726533285,10.0411592312,-0.340170041197,5.23975968445,1.07989288607,-2.55118382246,-1.55358548072,-1.6720162382,0.334401220437,-0.0232214315845,-0.740572906145,-1.62262491901,1.11870839238,-3.61708055581,0.459780900288,-1.68774932271,1.38147017444,0.996551729923,1.39157643606,0.383362521559,0.628000510699,1.25511096441,-0.80716699576,2.5125913236,-1.40571182898,1.05409248357,-0.738239102858,-0.171263774564,0.431461152105,-0.395966741528,-0.419844928582,-0.329707112118,-0.705392825763,0.21530152161,-0.203278133997,0.413854490049,0.410984082874,0.684270868505,0.441593566975,1.37748219481,1.07610821187,0.305465962074,0.707198942997,-0.733963294653,-0.0938702977929,-0.128422322562,-0.0991187761644,0.215869398941],[-33917.4482255,-947.627643048,-438.294457367,-2336.20924856,-495.932080669,924.320317751,1136.05551722,456.902719479,-1409.44834407,63.3369615271,147.285851511,91.1824459604,-436.39451742,-1400.22666111,-439.463879363,-4.64957295755,-516.459683198,-72.2886706696,-730.800016632,85.380138298,193.160048744,148.422367183,105.036582767,-605.801278712,166.385017406,-127.00434503,24.0663118309,143.35730202,29.2999541127,386.05184727,13.2054365434,-147.354857601,-53.1965485555,20.606159072,182.135824172,75.6434386823,-8.19774192594,100.704488193,7.91450062656,-6.61314255776,-26.0544011575,-24.1682429064,-34.3696776788,16.3614146417,-20.7038268323,-12.6106760956,-25.426343444,-89.2889487744,14.6221160826,7.89047751658,5.44176183188,-12.1038000441,-5.07849665757,-3.04304539595,-9.06219808592,29.8009185954,-15.9519583692,-14.1870914641,-14.0131684509,-3.94257508133,-2.76901935579,14.606573546,15.0562333841,3.62218017889,1.52662977494,-3.60540612962,-4.75959018543,5.55681101612,-1.25156415982,0.110200437921,2.18367527227,1.56549348472,-4.97687811061,10.089568433,-0.45078001077,5.30770146911,0.976659450075,-2.49397519833,-1.46612101052,-1.59597281308,0.306307997182,-0.0292415046258,-0.741268221046,-1.59280923436,1.12306036433,-3.59950901809,0.411538863705,-1.67642024705,1.36982382536,0.935110322115,1.40821429141,0.336631775107,0.669454963528,1.21152283048,-0.795392907265,2.51804661976,-1.37665214506,1.0674026968,-0.738771568926,-0.182310024137,0.419993042634,-0.391859711786,-0.412972929858,-0.318807849896,-0.698099958372,0.212457110678,-0.193581398974,0.404301929904,0.408825851568,0.683170108269,0.420961518698,1.38103405554,1.05640118012,0.303439416552,0.702960313111,-0.731377380159,-0.0883911677922,-0.131005559848,-0.104558558405,0.212480136327],[-33844.6082483,-973.848232167,-468.884213807,-2359.13292893,-508.369251589,899.145819857,1140.72661579,430.953941506,-1387.31746844,33.3166741143,143.523071633,89.0032318183,-450.269154089,-1422.21158055,-432.305953041,-7.44730889681,-509.146209162,-79.9536570056,-727.887418348,99.9242454841,191.147290742,159.639006896,104.539308257,-594.233383403,164.262519356,-124.580448133,25.5603771441,140.308302234,29.7855680885,387.027898016,16.9651683448,-148.807036989,-53.4081120534,23.7438963565,179.686358839,75.3605085623,-7.19486039174,100.341813335,8.43245792778,-7.1521545759,-25.195040577,-23.6196824675,-34.7561184865,15.9210699863,-20.1916080291,-12.0794935869,-25.234272416,-89.2387953089,14.5654779958,8.20735100697,5.36834675236,-11.7364508509,-5.56432501016,-2.92177901075,-9.19606806987,29.3550718492,-15.7364128121,-14.5514710744,-13.7280687113,-4.03499847214,-2.70988488024,14.1505466112,15.1338663856,3.60308773578,1.57534096169,-3.61721223629,-4.63238189881,5.46463607698,-1.28838911685,-0.0162707095978,2.13338366074,1.5519784388,-5.18371785705,10.1222223646,-0.546194797451,5.38735894261,0.870109334074,-2.44090626035,-1.38716812189,-1.51228820061,0.274482121884,-0.0442339249742,-0.743148460887,-1.5583723336,1.12914644868,-3.57604818543,0.369425304676,-1.66486275885,1.35608448498,0.877059331996,1.42025429967,0.296810159466,0.714326551546,1.16907290282,-0.783372737698,2.51785317268,-1.3458442428,1.08054845561,-0.737056897173,-0.192711520517,0.405358981482,-0.388238447618,-0.406541831165,-0.308738506418,-0.689584084774,0.211032031778,-0.184716770034,0.395929615307,0.406344403537,0.681190733606,0.402085689911,1.38444455934,1.03767405247,0.30265883917,0.697453212016,-0.728007317307,-0.0825807847268,-0.132826037327,-0.10977115441,0.2084741862],[-33760.3303873,-1003.38299522,-498.571465812,-2383.40648654,-519.500177495,876.654434043,1146.64890808,409.894438991,-1363.71876069,3.5606243501,140.925505886,87.8068875555,-463.364074352,-1440.49853289,-424.621963547,-10.1216295139,-501.644229451,-88.0516264342,-724.777852591,112.736166008,188.595800831,169.798092481,103.08049359,-583.530106418,162.172918211,-121.794735369,26.8536318103,136.963932942,29.5376073669,387.542197464,20.0898958882,-150.494845535,-54.0582364228,26.6384177581,177.488549506,74.9590018372,-6.00011055011,99.9382354935,8.97827065171,-7.80679544811,-24.3764822508,-23.3357093589,-35.2380977629,15.2633157918,-19.7902776394,-11.408795074,-24.8866750424,-89.0259679611,14.4352478625,8.55880079164,5.32809778786,-11.320063816,-6.02929004368,-2.80087458511,-9.38214489623,28.8936668954,-15.5859805524,-14.8984823606,-13.4305219187,-4.06602660177,-2.60691417084,13.6745363956,15.1835650729,3.55954999326,1.61631678039,-3.62504753985,-4.48074220677,5.38461512456,-1.31413496503,-0.132949244346,2.08680896814,1.51856123267,-5.37467710182,10.1382542333,-0.624003209829,5.47912236896,0.76277467833,-2.39160937314,-1.31772632474,-1.42151673227,0.239384942027,-0.0675138107564,-0.746379951519,-1.51984638057,1.13667491896,-3.54706185032,0.333337653201,-1.65366121265,1.34035053661,0.822710046525,1.4276784471,0.264126002897,0.762576438167,1.12867678022,-0.770536890224,2.51193671669,-1.31303886711,1.09339276577,-0.732610170806,-0.202435762577,0.387852361939,-0.385139100967,-0.400509723441,-0.299562946008,-0.680006964421,0.211004028943,-0.176901737352,0.388735196387,0.403478352192,0.678396086926,0.385015604925,1.38773126327,1.02014853723,0.303321374002,0.69081841152,-0.723640073972,-0.0764901836057,-0.133625581003,-0.11458579722,0.203895226726],[-33668.5332016,-1032.4418815,-521.679867192,-2410.0791465,-529.702615901,856.573476866,1155.14581583,395.693383046,-1339.01514184,-25.9468960417,139.213705283,87.7364845772,-475.263128361,-1454.55319505,-417.046398932,-12.813325998,-494.106824349,-96.572092469,-721.474722756,123.91972644,185.738323552,178.880703526,100.657171443,-573.773632989,160.093607345,-118.731593514,28.0107654953,133.31105467,28.6364156869,387.630005908,22.6259334986,-152.34998511,-55.1414693394,29.3038111369,175.596860452,74.4428332326,-4.63759394063,99.506760636,9.5430104085,-8.5541642488,-23.6007239584,-23.2752023887,-35.7785166833,14.404686927,-19.4729755706,-10.5895997687,-24.3727458365,-88.6554338479,14.2397554796,8.94037569862,5.32103582886,-10.8601964166,-6.46891442285,-2.68305335139,-9.60974843186,28.425127355,-15.4946375532,-15.2202352641,-13.1189310069,-4.03086794222,-2.45991285325,13.1836561372,15.205326648,3.49441394256,1.65029948172,-3.63007672456,-4.3064743461,5.3164636896,-1.33015691533,-0.239366562185,2.04299864313,1.4668433006,-5.54818308648,10.1378632139,-0.682536183814,5.58323864546,0.657035722846,-2.3450339004,-1.25824395571,-1.32411861133,0.201423215924,-0.0982512782323,-0.75117781595,-1.47763867108,1.14515774613,-3.51299864888,0.30288958912,-1.64350241997,1.32280266406,0.771888745334,1.43071966596,0.238461811971,0.81424174942,1.09112323762,-0.756111294549,2.50046673451,-1.27785193646,1.10583783917,-0.725072806267,-0.211472243606,0.367779169133,-0.38261130115,-0.394804450455,-0.29131904162,-0.66949954678,0.212265170912,-0.170334178618,0.382664156376,0.40006480843,0.674882415383,0.369681429166,1.39094513846,1.00399178382,0.305582704455,0.683209330669,-0.718065402031,-0.070195678069,-0.13319392978,-0.118893180452,0.198800506644],[-33573.6275966,-1057.32231932,-534.382005072,-2439.77136812,-539.907071728,838.716307737,1166.65504074,389.680256016,-1313.52190766,-55.2785998302,138.271384609,88.7655440558,-485.840233196,-1464.20554964,-410.208781681,-15.5908661743,-486.609468546,-105.450435629,-717.992199394,133.620168611,182.711521093,186.902288466,97.3480962314,-564.996747636,158.006952144,-115.457773009,29.1042654301,129.351556886,27.1962717712,387.315165774,24.6203803422,-154.305189458,-56.6461306151,31.7641074929,174.034801353,73.8109623653,-3.12724285036,99.0588811445,10.122425274,-9.36703504821,-22.8705823408,-23.3919646438,-36.3470443943,13.3643535694,-19.2078098184,-9.62290202339,-23.6883045016,-88.1369411502,13.9871366833,9.34795746449,5.34568322604,-10.3615445042,-6.87833052657,-2.57074678378,-9.86505193762,27.9535554096,-15.4551611302,-15.5111640263,-12.7927383373,-3.9272432764,-2.2701443678,12.6827994866,15.2012149569,3.41054563608,1.67771189515,-3.63354078435,-4.11132531902,5.25941981913,-1.33780045216,-0.335009420762,1.99987456439,1.39909990368,-5.70385846726,10.1218095517,-0.720518920317,5.69942040015,0.555177045937,-2.29975848768,-1.2085902998,-1.2204439698,0.161001072925,-0.135625537044,-0.757767799209,-1.43211375307,1.15393022015,-3.47430698724,0.277607447598,-1.63510250146,1.30383101458,0.724022844525,1.42981975777,0.219487281408,0.869269467295,1.0571427656,-0.739275383574,2.48385583885,-1.23979773555,1.11783497381,-0.714261236255,-0.219802274087,0.345437163589,-0.380705600345,-0.389362932359,-0.28403384823,-0.658166028746,0.214654837091,-0.165162593813,0.377671405503,0.395860889261,0.670795023202,0.355930103877,1.39413390741,0.989341130818,0.30952155085,0.6748122065,-0.711088214242,-0.0637796017692,-0.131383262218,-0.122641392649,0.193257084802],[-33479.9778114,-1077.59330294,-536.417208009,-2472.12104615,-551.660281507,822.400508116,1180.12945148,391.285382856,-1287.15222016,-84.4944573133,138.147092123,90.5403434038,-495.419217121,-1469.63399739,-404.82222638,-18.4398008395,-479.101428638,-114.512252218,-714.334561572,141.975789883,179.548531382,193.797649699,93.3100519539,-557.224189453,155.889230986,-111.992792999,30.2198561717,125.116696189,25.3642180912,386.613765472,26.1048217021,-156.27599514,-58.5748492,34.0634581772,172.782151249,73.0536781017,-1.48355241412,98.6056225789,10.720689195,-10.2058771548,-22.1847209736,-23.6376045934,-36.9169567346,12.1538460346,-18.9561945904,-8.52366924372,-22.8353020451,-87.4852541535,13.6833596795,9.77599174499,5.39938019859,-9.82651461534,-7.25162660768,-2.46491540462,-10.1307410504,27.4800094802,-15.4603464315,-15.7653660328,-12.4537579196,-3.75416709981,-2.04155522222,12.1763129299,15.1751426433,3.31078654,1.69825281574,-3.63704444134,-3.89696657045,5.21229591134,-1.33804821025,-0.418473099661,1.95484362708,1.31834467698,-5.84203730915,10.0908073045,-0.736722005982,5.82673382527,0.459580465301,-2.25376115409,-1.16778695228,-1.11073151733,0.118669931291,-0.179001298624,-0.766423150699,-1.38369902509,1.16216391089,-3.43135577862,0.25707157912,-1.62915527122,1.28411794087,0.678251717989,1.42558484928,0.206917075549,0.927500244539,1.02755467179,-0.719228129637,2.46277404707,-1.19832229044,1.12936164391,-0.70017571579,-0.227368531723,0.321102674174,-0.379476544717,-0.384163515773,-0.277762337673,-0.646100470298,0.217954390579,-0.161474574711,0.373790816895,0.39058440663,0.666344386214,0.343577749476,1.39732805932,0.976345869925,0.315143825161,0.665871076121,-0.702510931192,-0.0573088343436,-0.128117010093,-0.125831349832,0.187330082678],[-33390.876551,-1095.98667974,-533.136607975,-2505.78281,-566.504809426,806.029987203,1193.86528471,397.715580753,-1259.49585202,-113.499656739,138.9541313,92.5103703919,-504.906682258,-1471.2595619,-401.846931866,-21.3118123212,-471.432959853,-123.490976297,-710.4652747,149.097072963,176.2656793,199.370292107,88.7904555608,-550.53147572,153.699726544,-108.327917573,31.4560749278,120.671675388,23.3110967225,385.55614266,27.0899874326,-158.156183901,-60.9497524016,36.2803635822,171.783324986,72.1528112825,0.27902098988,98.1587750739,11.3472314352,-11.0202214297,-21.5344017793,-23.9619598888,-37.4586198791,10.7746551247,-18.6674783445,-7.32307442812,-21.8199815261,-86.7224675617,13.3328446852,10.2164309627,5.47877994393,-9.25683980163,-7.5817416231,-2.36451613,-10.3866146163,27.0053392381,-15.5040264881,-15.9749404847,-12.1067682982,-3.51026596825,-1.7807353185,11.6693369552,15.133353867,3.19820914435,1.71089349552,-3.64254149439,-3.6654729042,5.17363915873,-1.33167771053,-0.487587140448,1.90540006275,1.22823770959,-5.96312854872,10.0454844327,-0.729467555822,5.96354679983,0.372864671889,-2.20442579161,-1.1341895222,-0.995062718719,0.0751962234035,-0.22785954522,-0.777454713547,-1.33301082649,1.16887650525,-3.38458737144,0.240927423489,-1.62631080061,1.26463785895,0.633616481906,1.41873523291,0.20070216654,0.988665089329,1.00339530958,-0.695153912255,2.43822830929,-1.15284006982,1.14043827709,-0.682952490758,-0.2340623865,0.2950722144,-0.378980136962,-0.379231419273,-0.27259231978,-0.633438412023,0.22189176176,-0.159323169491,0.371130078872,0.383944748591,0.661805393657,0.332478876224,1.40056881665,0.965224705071,0.322408696324,0.65671123806,-0.692129586418,-0.0508406400368,-0.123346567557,-0.12851190465,0.181098520693],[-33308.0183172,-1119.07716423,-533.417334101,-2538.44581604,-586.00181152,787.457098491,1205.65481915,404.448502283,-1229.82054322,-142.022243177,140.872041558,93.8960828134,-515.627597994,-1469.79062992,-402.541201665,-24.1249631101,-463.365109205,-132.060997545,-706.341151685,155.080988545,172.829108503,203.287161234,84.0721012524,-545.060861064,151.384713902,-104.431134444,32.9206492662,116.102730551,21.2208940724,384.174690934,27.5628245218,-159.838493905,-63.8135754491,38.5166208748,170.953652303,71.0829099901,2.14797710616,97.7309629083,12.0153529038,-11.7516034763,-20.9063443958,-24.3148934945,-37.9447485633,9.21775879173,-18.2862986157,-6.06867616083,-20.6528156896,-85.8773085105,12.9379696589,10.6595341474,5.58065768691,-8.65382802935,-7.86034719165,-2.26667672883,-10.6108819088,26.5299435459,-15.5822048064,-16.131909911,-11.7602062211,-3.19431272468,-1.49745198268,11.1681675015,15.0834011533,3.07572547857,1.71397406505,-3.65216072629,-3.41914380281,5.14207301156,-1.3192411039,-0.539532851205,1.84926177531,1.13269595494,-6.06783124686,9.98609797342,-0.697032458666,6.1070962556,0.297727177167,-2.1490582217,-1.10578822716,-0.873517572335,0.0314538951477,-0.281819855308,-0.791220979879,-1.28082354614,1.1730118635,-3.33450462887,0.228989711065,-1.62715294578,1.24659666836,0.589073793224,1.41001305593,0.200918978947,1.05221832652,0.985837084749,-0.666409659202,2.41148891954,-1.10289366106,1.15110346927,-0.662850668909,-0.239720231332,0.267633399029,-0.379281364182,-0.374636547899,-0.268637128456,-0.620361612863,0.226186800075,-0.15873346958,0.369865739631,0.375650014333,0.657499543934,0.322527781088,1.40387738342,0.956241204436,0.331196792645,0.647721067783,-0.679787477438,-0.0444200403047,-0.117058137846,-0.13076900856,0.174659125138],[-33232.5669685,-1150.06970082,-543.323946552,-2569.16692998,-610.519534444,764.775005396,1214.27793317,407.589755829,-1197.74493298,-169.886346531,143.912634076,94.154758854,-528.534302769,-1466.09483125,-407.737659557,-26.8490090066,-454.82699433,-139.980542172,-701.912335195,160.054480811,169.151070326,205.304804421,79.3747755908,-540.897182616,148.903187845,-100.318425752,34.6889875012,111.482294297,19.2388294856,382.499645403,27.526430482,-161.241811993,-67.1675753102,40.8602152488,170.203270625,69.8289136862,4.10716249741,97.3312306841,12.7272219624,-12.3548568798,-20.2853833287,-24.6510076376,-38.3579510985,7.48194197403,-17.773128865,-4.80990737887,-19.3555898581,-84.979922609,12.5032202562,11.0972226672,5.70368374584,-8.02162427335,-8.08205423734,-2.16784850294,-10.785998224,26.0530911342,-15.6915610627,-16.2329540846,-11.4222624724,-2.8095489374,-1.20339993492,10.6785850282,15.0320626015,2.9462148983,1.70694535624,-3.66726178207,-3.16049643424,5.11627448998,-1.30129962381,-0.572667387685,1.78478701865,1.03497533932,-6.15765155236,9.91321250885,-0.639426104382,6.25390691472,0.235855518461,-2.0854781856,-1.08065705033,-0.746439614476,-0.0118177390822,-0.340248010431,-0.8079256348,-1.22781245902,1.17374372932,-3.28170485453,0.220992876038,-1.63202840497,1.23091049914,0.543608929929,1.40012417514,0.207299564329,1.11740786621,0.97564696805,-0.632708400091,2.38375624371,-1.04841032706,1.16136482373,-0.640310389909,-0.244222993621,0.239078285915,-0.380449925354,-0.370397836195,-0.265926653699,-0.607090461115,0.230592201287,-0.15967466616,0.37010317783,0.365489785141,0.653705315046,0.313614202763,1.40724888496,0.949548190988,0.341293961834,0.639237114042,-0.665465909401,-0.0380826753211,-0.109328512923,-0.132699707501,0.168106665734],[-33164.4314424,-1182.09689822,-563.178113968,-2599.33761546,-638.636763997,737.358627154,1220.27471684,406.026466019,-1163.71639901,-197.131245849,147.928107169,93.2628887934,-543.70805997,-1461.1101762,-417.354750994,-29.5255515696,-446.03970335,-147.17487431,-697.123831622,164.218763498,165.10265137,205.454373157,74.8292137985,-537.969405573,146.242083062,-96.0956308388,36.7758540386,106.844910613,17.4530080027,380.550854225,27.0117673595,-162.331512027,-70.9393125642,43.3550009305,169.452601542,68.3915599169,6.13385660645,96.9598763044,13.4659986681,-12.8130072134,-19.6577823706,-24.9339192479,-38.6948795928,5.5852479924,-17.1143478195,-3.58783359172,-17.9674250869,-84.0590897855,12.0372027682,11.5256390005,5.84856472086,-7.36913491814,-8.24625928176,-2.06436440017,-10.9010017245,25.57251912,-15.8290218997,-16.2820447146,-11.0978452312,-2.36698279253,-0.910609905946,10.2046969,14.9847012997,2.81261747433,1.69110444778,-3.68759850291,-2.8920922573,5.09486312237,-1.27830113871,-0.587332798037,1.71113758705,0.936963541463,-6.23483711695,9.82830104962,-0.559074839633,6.40018663396,0.187247345211,-2.01235907739,-1.05720144417,-0.614757209088,-0.0541120091484,-0.402059856025,-0.827446839964,-1.1743008072,1.17059006962,-3.22683142493,0.216492223044,-1.64080818606,1.21794409897,0.496416947041,1.38969223659,0.219054514175,1.18339449958,0.972824482402,-0.594139817133,2.35597403452,-0.989840675423,1.17118768377,-0.616035155334,-0.247530335401,0.209709551756,-0.382558948382,-0.366427474656,-0.264346469144,-0.593849220452,0.234925199646,-0.162027430612,0.371810288452,0.353385100647,0.650585050353,0.305620078622,1.41068362879,0.945094305887,0.352392926188,0.631452354193,-0.649342041113,-0.0318721387047,-0.100378243295,-0.134397422465,0.161524969338],[-33101.7485486,-1210.25628694,-590.637773053,-2629.90965662,-669.006845182,705.247753373,1224.06696634,398.780535684,-1128.05438305,-223.708481154,152.781283309,91.0641917259,-560.922877856,-1455.86750514,-431.076467206,-32.1308182622,-437.268126163,-153.582688087,-691.996129755,167.791881401,160.440586375,203.738476484,70.4850944093,-536.197953378,143.389874823,-91.8679252323,39.1687519909,102.202543108,15.9210023456,378.311359399,26.0163337496,-163.093875938,-75.0506241342,46.0314834559,168.613679866,66.7701143136,8.21128421127,96.612438842,14.2105880118,-13.1187053526,-19.0130715547,-25.1381424759,-38.9598296422,3.54244075382,-16.3106435295,-2.44314154818,-16.5362968875,-83.1404504091,11.5472608423,11.9428324706,6.01672492621,-6.7046911471,-8.35143586682,-1.95216632329,-10.9478824602,25.0849278665,-15.9955195444,-16.2852002595,-10.7920598449,-1.88014911211,-0.632541478212,9.75002029052,14.9448985784,2.67709663788,1.66760506117,-3.71214724723,-2.61587953216,5.07677576203,-1.25012542726,-0.583833244015,1.62823954109,0.839302651772,-6.30089271144,9.7324723372,-0.458995846454,6.54162041584,0.151218455408,-1.92875389664,-1.03384198138,-0.479585396822,-0.094974126276,-0.466308008367,-0.849607592732,-1.1204295041,1.16320555151,-3.17037877332,0.215396873111,-1.6530040887,1.20791812361,0.44703083213,1.37915309504,0.235409447465,1.24926484408,0.977049413365,-0.551039017269,2.32890036305,-0.928020001485,1.18046414298,-0.590890955928,-0.249551914907,0.179770796084,-0.385698955567,-0.362659989094,-0.263768927014,-0.580835484194,0.239103053266,-0.165655887769,0.374996362277,0.339333120212,0.64822971463,0.298515877567,1.41416550014,0.942756679529,0.364134685367,0.624491275918,-0.631700045484,-0.0257885001735,-0.0905103895746,-0.13592988629,0.154987686608],[-33042.172759,-1234.76343727,-620.22506473,-2660.59800147,-701.127044806,669.67862463,1225.91931403,386.286837682,-1090.71362928,-249.518205542,158.457718509,87.1489370234,-579.476534594,-1451.45790765,-448.306294961,-34.5425970711,-428.759089828,-159.167966588,-686.617611041,171.031393692,154.876587492,200.209317618,66.3792048051,-535.468014647,140.338528944,-87.7193242777,41.8257008669,97.5539331817,14.6778406177,375.735900347,24.5322595118,-163.52974218,-79.3906561314,48.9050560325,167.622457664,64.9600453564,10.3298057184,96.2793299229,14.9395371473,-13.2757069765,-18.3441688571,-25.2450669844,-39.1599062571,1.37434714666,-15.3702864422,-1.40627546837,-15.1125796194,-82.2427969434,11.0387180412,12.3485154625,6.20957646862,-6.03497917278,-8.39608615729,-1.82636249893,-10.9212017916,24.5872672907,-16.1930587977,-16.2487369049,-10.5065166494,-1.36282975793,-0.379814635732,9.31864546669,14.9165488038,2.54115569034,1.63729577753,-3.73930844295,-2.33316614432,5.06118757843,-1.21595659293,-0.562518820119,1.53661388192,0.741718446065,-6.35627651499,9.62716162515,-0.342164581231,6.67445327451,0.126760322096,-1.83345323953,-1.00923182321,-0.342004100276,-0.133927752925,-0.532255457858,-0.874137518783,-1.06623272225,1.15137410997,-3.11268863929,0.217847862196,-1.66785836481,1.20083248407,0.395379618873,1.36879995636,0.255752517551,1.31426381918,0.987852110897,-0.503570333412,2.30318276931,-0.863873049578,1.18905457572,-0.565777192796,-0.250139060872,0.149451614309,-0.389953425237,-0.359065268072,-0.264061309145,-0.568224754632,0.243120514992,-0.170413299021,0.379673911695,0.323398037858,0.646642402893,0.292367700039,1.41769903311,0.942378110581,0.376233266826,0.618425023666,-0.612817380011,-0.019815357255,-0.0800347283709,-0.137349659236,0.148586654631],[-32984.5570903,-1255.29524146,-647.041583088,-2690.85026001,-734.630273366,632.105328171,1226.71006165,370.485660321,-1051.57748335,-274.620674691,164.953486039,81.2734864527,-598.397779367,-1448.70659937,-468.243345462,-36.6065599371,-420.815891864,-163.936789304,-681.055775553,174.140243587,148.191601814,194.990173789,62.6033626918,-535.596767948,137.093597848,-83.737111499,44.6781529324,92.882653198,13.7183111204,372.779463871,22.5565603286,-163.630372476,-83.8152609725,51.9833654778,166.446279335,62.9596279673,12.4810851691,95.9470376404,15.625781078,-13.3014872137,-17.6455260987,-25.2455719941,-39.3004877878,-0.889903245205,-14.3013867109,-0.490435550129,-13.7442605964,-81.3751900902,10.5164924483,12.7445433978,6.42872019611,-5.36688916012,-8.38047229841,-1.6825963036,-10.8193851869,24.0769704301,-16.4228186167,-16.1774280245,-10.2376087521,-0.828442487851,-0.158497726109,8.91481349564,14.9051481163,2.40607496108,1.60161117726,-3.76704421956,-2.04494343472,5.04750776895,-1.17487748292,-0.524234884902,1.43693130948,0.643145672272,-6.40070394353,9.51437565232,-0.211390949632,6.79617715464,0.112815126406,-1.72458459851,-0.982215522755,-0.203092026719,-0.170502857319,-0.599182987756,-0.900616007311,-1.01158623701,1.13512193258,-3.05406232585,0.223972208699,-1.68458333694,1.1963136052,0.341642935404,1.35879889719,0.279678525968,1.37790300484,1.0046632544,-0.451614957658,2.27931647713,-0.79825346876,1.19675897871,-0.541506056026,-0.249155068296,0.118900278362,-0.395379665621,-0.355581627461,-0.265055449541,-0.556175142634,0.247009421478,-0.176159532744,0.385801501103,0.305686014321,0.645719933895,0.287296105965,1.42130463736,0.94375662893,0.38850002163,0.613267679458,-0.592919744903,-0.0139592372466,-0.0692441579669,-0.138713783329,0.142419625808],[-32929.6587054,-1269.96746296,-670.150189743,-2720.34438089,-769.03925798,593.077863766,1228.05422128,352.911116958,-1010.52766029,-299.222347147,172.143681771,73.5434536008,-616.923862166,-1448.14626489,-490.26598571,-38.1676546192,-413.816013298,-167.915165539,-675.332406482,177.188832335,140.22098353,188.144515556,59.284937702,-536.413094774,133.673164113,-80.0247552331,47.644214685,88.1610410304,12.9911807683,369.402982834,20.0718960501,-163.374246146,-88.1836097967,55.2700966406,165.065866638,60.7721747498,14.6557428647,95.6005707188,16.2354071356,-13.22334075,-16.9129147981,-25.140309387,-39.3879221301,-3.21899195647,-13.1132761885,0.300847051479,-12.4734230233,-80.5391354475,9.98550147786,13.1345929674,6.67602301608,-4.70858300696,-8.30640007931,-1.51751153712,-10.6440131774,23.5509913356,-16.685495477,-16.0749314707,-9.97970740777,-0.289263760448,0.0274755331739,8.54281740036,14.9163725707,2.27298440414,1.56273929082,-3.79311767342,-1.75219752897,5.03551783508,-1.12608384902,-0.470221527807,1.32968890529,0.542043649308,-6.43358384501,9.39620490185,-0.0693271491673,6.90482207136,0.108425487397,-1.60017192512,-0.951925440372,-0.0639528732152,-0.204283983229,-0.666336162013,-0.928496912575,-0.956248636602,1.11469618502,-2.99480142599,0.233828136839,-1.70248512207,1.1937243117,0.286131657622,1.34921042878,0.306887303059,1.43972517613,1.02681697319,-0.395045436425,2.25757839495,-0.731998429447,1.2032699038,-0.518788869714,-0.246498305824,0.0882384945433,-0.402005012495,-0.352103003062,-0.266560369948,-0.544830004214,0.250806176,-0.182746182471,0.393288718418,0.286326291453,0.645298252238,0.28343910983,1.42498426609,0.946646373274,0.400777370645,0.608978856254,-0.572218743677,-0.00825699225151,-0.0584195974324,-0.140095239128,0.136581716445],[-32878.7486574,-1278.63125276,-691.240112971,-2748.7903102,-803.834922409,552.42443642,1231.5500226,334.368892102,-967.278167055,-323.5025728,179.847016654,64.1368572014,-634.451852589,-1450.08681305,-513.906723371,-39.0677774121,-408.15212752,-171.113343984,-669.46208732,180.1799666,130.812863309,179.655166,56.5584819919,-537.808385114,130.091964392,-76.688380172,50.6442203877,83.3579717508,12.4091292075,365.56176185,17.0517265883,-162.729556128,-92.3666346982,58.7634305825,163.468951102,58.4031326396,16.8464769885,95.2234484784,16.7339365051,-13.0728168794,-16.1450387515,-24.9324505921,-39.4304132805,-5.57912527511,-11.8229452029,0.969273802688,-11.3366274686,-79.7293879329,9.45037403595,13.5234210601,6.95329071839,-4.06830017346,-8.17630040849,-1.32850824217,-10.3981218976,23.0048247469,-16.9806506218,-15.9454765804,-9.72697671849,0.244107248581,0.174847705959,8.20725861588,14.9550533034,2.14296178585,1.52318040353,-3.81528305181,-1.4557188302,5.02531918788,-1.06891492146,-0.401934598285,1.2151275966,0.436835855706,-6.45428911045,9.27449521499,0.0813230810321,6.99842644631,0.112693315421,-1.4582414164,-0.917800004161,0.0744482335571,-0.234899258549,-0.732969965954,-0.95721147051,-0.899899871112,1.09046985493,-2.935151259,0.247384687503,-1.72097431506,1.19231721904,0.229199858867,1.33997649303,0.337010035334,1.49918980775,1.05354550879,-0.333815217146,2.23801465902,-0.666007024269,1.20814588723,-0.498270031902,-0.24209569461,0.0575670089665,-0.409830080844,-0.348507524168,-0.268374773132,-0.534314696442,0.254525084072,-0.190022271202,0.401994146266,0.265461827385,0.645184507814,0.280906051222,1.42869949944,0.950760686784,0.412915494445,0.605465424853,-0.550927749873,-0.00276093502185,-0.04782624679,-0.141570140045,0.131174551262],[-32832.357834,-1283.85232457,-710.814397734,-2775.3329888,-838.571305138,509.881709931,1237.75335676,315.941729354,-921.306035653,-347.565663406,188.053175112,53.0684407343,-650.237574025,-1454.73324462,-538.904334624,-39.1601761108,-404.156303012,-173.520920006,-663.453096054,183.099752058,119.752994032,169.44590354,54.513317584,-539.735303036,126.353435858,-73.8159727213,53.5906053493,78.4442350188,11.8661212017,361.19694474,13.4733320948,-161.67248743,-96.2592733061,62.4407896566,161.634391764,55.8570013252,19.0465081395,94.7953577269,17.0913703134,-12.8818635395,-15.3441018018,-24.6246838228,-39.4451766981,-7.93847664359,-10.4587158171,1.518387869,-10.3648579344,-78.9355065269,8.91418634737,13.915563977,7.26149279725,-3.45300526042,-7.99399255448,-1.1130839052,-10.0851502367,22.4317502705,-17.3060248408,-15.7951702127,-9.47432214851,0.76188718969,0.279967794529,7.91285669794,15.0249658627,2.01707876317,1.48548182672,-3.83144867862,-1.15606289323,5.01699782596,-1.00251016267,-0.320637009484,1.09322223929,0.326173132071,-6.46278242333,9.15066176829,0.237626531405,7.07492796913,0.125122632938,-1.2970664474,-0.879344842209,0.210957546553,-0.261917836114,-0.798414889737,-0.98613700053,-0.842218154307,1.06287482457,-2.87521337815,0.264483192426,-1.73953300701,1.19132116616,0.171102019418,1.33098139706,0.369620013249,1.5556208364,1.08407873664,-0.268069297908,2.22047713031,-0.601283312936,1.2108515943,-0.480486447546,-0.235881703514,0.026962965256,-0.418808075779,-0.344673106226,-0.270309934219,-0.524737490216,0.258124208165,-0.197803303255,0.411752396031,0.243251118937,0.645186503144,0.279751296103,1.43237019189,0.955777911942,0.424745151224,0.602613213029,-0.529288866735,0.00248051730185,-0.0377230120708,-0.143214714251,0.12629540938],[-32789.9542888,-1284.50527681,-729.441596623,-2799.55255296,-871.743500321,465.237537646,1247.78308725,299.372264682,-872.352192304,-371.438478169,196.873182342,40.7292642668,-663.412846791,-1461.9841091,-564.879334098,-38.3781022381,-402.172101534,-175.140796725,-657.219257781,185.908172444,106.920089251,157.492964626,53.2816971984,-542.144312599,122.453062133,-71.5160175887,56.378863835,73.400237123,11.2423866813,356.277922233,9.33340959608,-160.165242627,-99.7553238587,66.2666287192,159.545993937,53.1419151144,21.2385107867,94.2920543437,17.2747112993,-12.6863598691,-14.5107545033,-24.22014618,-39.4487711222,-10.2597022024,-9.05114002469,1.95716147181,-9.58452981488,-78.141365594,8.38107498348,14.3141265419,7.6005849354,-2.87221919368,-7.76599570655,-0.869231422431,-9.70970074249,21.8256591435,-17.6564967031,-15.6292731022,-9.21499556086,1.25552326799,0.341881618015,7.66469530744,15.1300558048,1.8970752929,1.45260408095,-3.83938876515,-0.854542463548,5.01026868344,-0.926405804726,-0.228088631987,0.963988739118,0.209072940164,-6.45895514185,9.02671840929,0.396951697163,7.13316767798,0.145604662658,-1.11488869229,-0.836140673635,0.34440486235,-0.284787280504,-0.861749623857,-1.0145104398,-0.782934601359,1.0323758807,-2.81524808381,0.284636375502,-1.75771534395,1.18984771708,0.112163710866,1.32219000614,0.404368214595,1.60850553956,1.11769836494,-0.197900840233,2.20477339698,-0.538742514365,1.21085286309,-0.46588619347,-0.227833217742,-0.00341935706674,-0.428843793276,-0.340437847049,-0.272162787206,-0.516236789705,0.261478966274,-0.205905123994,0.422308297522,0.219877868643,0.645099157388,0.280012825519,1.43595622162,0.961378736046,0.436162417388,0.600302586383,-0.507505883474,0.00740576187657,-0.028332839563,-0.145114551112,0.122051323247],[-32750.7826631,-1275.11325562,-749.45325997,-2821.66881148,-901.07596507,418.309033369,1262.70617644,286.665019501,-820.545525567,-395.091730411,206.470276084,27.890343052,-673.174267518,-1471.36919864,-591.315991851,-36.7382466778,-402.510600088,-175.990961931,-650.583420263,188.503961305,92.3123139883,143.836244648,53.0405432128,-544.9712216,118.386772703,-69.9043655065,58.8889865027,68.2229066398,10.4161706593,350.802762528,4.64289955432,-158.158157097,-102.763886854,70.193585134,157.184510017,50.2705034441,23.3950064074,93.6863569557,17.2502708482,-12.522815577,-13.6447379126,-23.7257556046,-39.4556951147,-12.5019508853,-7.62912691023,2.29906775753,-9.015864263,-77.3263128294,7.85627026538,14.720220914,7.96923980199,-2.33746267181,-7.50085014739,-0.596231695527,-9.27730316552,21.181458414,-18.0243348324,-15.4509415167,-8.9412892936,1.71772715181,0.362252784994,7.46759243358,15.2742935115,1.78523381563,1.42762267372,-3.83678756397,-0.553296153156,5.0043623735,-0.840617746581,-0.126347014293,0.827560151384,0.0850332435118,-6.44254461454,8.90518663693,0.557280921507,7.17286880364,0.174586363562,-0.910039882459,-0.787645596232,0.473513801585,-0.302861873767,-0.921857580411,-1.04145238448,-0.721844800296,0.999432355134,-2.75567079479,0.307088599015,-1.77512355606,1.18692908918,0.0527818849859,1.31367533503,0.441062100333,1.65749622226,1.1537580198,-0.123383361085,2.19070866132,-0.479147348081,1.20763699278,-0.454802527015,-0.217984739853,-0.0333481313593,-0.439805578819,-0.33561184924,-0.27373289134,-0.508958673187,0.264389865874,-0.214147024189,0.433334450539,0.195538198753,0.64472001033,0.281716393113,1.43944088758,0.967262163292,0.447117225038,0.598419371677,-0.485723426074,0.0119385339899,-0.0198475037902,-0.147357007521,0.118549755918],[-32715.0044325,-1253.06545714,-774.277412127,-2841.61716978,-925.56506753,369.030051011,1281.51408464,279.502183825,-766.024916237,-418.555982384,217.096988932,15.1267861178,-679.006729137,-1482.39074187,-617.748572664,-34.2304008792,-405.310227899,-176.082921765,-643.400792185,190.720007258,75.8826183203,128.551866341,53.9372518329,-548.171009592,114.169757665,-69.0470619422,60.9998421329,62.9229533219,9.29010405506,344.757979177,-0.581133253224,-155.626189047,-105.245136759,74.1533037921,154.503508685,47.2558469108,25.4901576937,92.9529041005,16.9943442516,-12.4187581519,-12.7518222831,-23.1533149451,-39.4888676618,-14.6311509705,-6.22183679985,2.55224065738,-8.67160770089,-76.4684003931,7.34299015806,15.1334918265,8.36514411567,-1.85775567425,-7.20666737099,-0.294591421825,-8.79275841281,20.49321384,-18.4008275891,-15.2628157589,-8.64882209793,2.1415042742,0.343268333039,7.3254419621,15.4605624206,1.68342515452,1.41288009981,-3.82154927301,-0.254342075559,4.99838046606,-0.744867819128,-0.0167917348336,0.684035066562,-0.0458071528044,-6.41382695475,8.78807491476,0.716892511147,7.19380327885,0.213142553651,-0.681770667803,-0.73301264694,0.596697332116,-0.315520167068,-0.977840466607,-1.0661020527,-0.658783170081,0.964442537909,-2.69674251625,0.331114558704,-1.79133138458,1.1817766802,-0.00673779439003,1.30551966217,0.479557444743,1.70209818961,1.19167409582,-0.0448692223464,2.17814949876,-0.423157246684,1.20075087005,-0.447429135796,-0.206395308423,-0.0626108226278,-0.45156237481,-0.330045152723,-0.274886047077,-0.502982919375,0.266637968526,-0.222303121346,0.444547229187,0.170411963473,0.643889968794,0.284829884969,1.44274792404,0.973146618145,0.457515035287,0.596899558406,-0.46408443544,0.0160012802405,-0.0124521723425,-0.15002930046,0.115883246105],[-32684.17838,-1219.08943527,-806.442996869,-2859.41965676,-945.280393341,317.583077596,1302.0302917,278.615773381,-708.930460059,-441.935956349,228.915978546,2.78965902028,-680.768571982,-1494.55248039,-643.629631762,-30.8004344793,-410.566958357,-175.46019463,-635.557430082,192.34838866,57.5781203892,111.749279985,56.0596610068,-551.722290521,109.837518331,-68.963292024,62.5888903567,57.5188604144,7.78842045603,338.1179254,-6.32135993143,-152.573390536,-107.195642574,78.069249841,151.442230396,44.1131339522,27.5020983731,92.0682996693,16.4905206493,-12.3930290797,-11.8425644836,-22.520655297,-39.576943794,-16.6214792521,-4.8576109658,2.71913463417,-8.55765772919,-75.5442247241,6.84295080586,15.5521665826,8.78582900701,-1.440064369,-6.89090962653,0.0336184680808,-8.26120999143,19.7544217737,-18.7767931269,-15.066819215,-8.33561419335,2.52126243146,0.288196865539,7.24077107862,15.6897587679,1.5928818393,1.40992520332,-3.7916183329,0.0403525365479,4.99117852725,-0.638916250343,0.0996022141841,0.533767956194,-0.182763312983,-6.37329213297,8.67676096373,0.874315495937,7.19590659166,0.262384560866,-0.430354839622,-0.67116677105,0.712387434461,-0.322268607514,-1.02898358249,-1.08762991655,-0.593605985478,0.927719684813,-2.6385640471,0.356110004829,-1.80581610923,1.17376885119,-0.0661564969593,1.29782848236,0.519737878854,1.74178844102,1.23091071105,0.0370063635775,2.16705095239,-0.37132851454,1.1897999125,-0.443845610954,-0.193145282909,-0.0910102686693,-0.463981801107,-0.323608273936,-0.275531936256,-0.498320329264,0.26801886628,-0.230118058881,0.455697055651,0.144660860437,0.6424905667,0.289277099631,1.44573308417,0.978756318051,0.46721080448,0.59572078569,-0.44272057384,0.0195215137746,-0.00629819672751,-0.153201471669,0.114126946924],[-32659.4452552,-1174.71055392,-847.412138396,-2875.21526314,-960.56138486,264.88037458,1322.0987186,284.012849722,-649.517325444,-465.257193578,241.976132407,-8.87430009161,-678.722987431,-1507.40335536,-668.364266691,-26.386175648,-418.130357305,-174.225518055,-626.930990215,193.159584313,37.4215144691,93.5991503849,59.437856672,-555.604446696,105.446443379,-69.6333978309,63.5366203582,52.0356206931,5.86192250603,330.84831236,-12.5503402473,-149.046232508,-108.624833272,81.8578769709,147.948972009,40.8622793446,29.4103367847,91.0120367579,15.7278069969,-12.4564922766,-10.9328515725,-21.8516349551,-39.7522844458,-18.4517248488,-3.56119558907,2.79867564173,-8.67244155084,-74.5306557138,6.3568583129,15.9730133426,9.22860161412,-1.08978759204,-6.56091190034,0.384188003119,-7.68913725868,18.958912931,-19.1416003183,-14.8642530858,-7.99984462149,2.85274889183,0.203118327904,7.21464786198,15.9610971905,1.51422199185,1.41972014463,-3.74512646365,0.328654270773,4.98150146982,-0.522986699824,0.221928839516,0.37728840125,-0.324640540166,-6.32175675145,8.57230970688,1.02812341939,7.17957090831,0.322985928954,-0.157266710789,-0.60121882836,0.819002051876,-0.322828925369,-1.074724151,-1.10523765676,-0.526252595826,0.889526605534,-2.58114006689,0.381530607308,-1.81803768367,1.16238890058,-0.125268784693,1.29083870245,0.561489634346,1.77616545413,1.27092055512,0.121397376726,2.15743740362,-0.324085297863,1.1744816168,-0.44399185139,-0.178361717923,-0.118354475827,-0.476919953252,-0.316178962766,-0.275620530435,-0.494922974531,0.268368727343,-0.23732486681,0.466552033441,0.118437194141,0.640457328006,0.294935514821,1.44821604969,0.983777261509,0.476043079476,0.594856473245,-0.421752329868,0.0224015592317,-0.00148374207703,-0.156927174005,0.113335781578],[-32637.202542,-1120.16523553,-896.528706054,-2888.65640108,-970.775405402,212.904996766,1340.335196,295.432206087,-588.281022744,-488.075965507,256.393297744,-19.4225435603,-673.242204459,-1520.37195313,-691.29137682,-20.998163687,-427.662989938,-172.519857375,-617.314452937,193.001159633,15.5934108949,74.4162625067,64.0602911693,-559.756069166,101.053314774,-71.0107450916,63.7275105174,46.5208156501,3.50792282534,322.934872524,-19.19478403,-145.125571045,-109.533293511,85.4343771704,143.993072801,37.5280845631,31.1887242509,89.7657575488,14.7020887236,-12.6110084126,-10.0409645429,-21.1658548512,-40.0479143912,-20.0961022193,-2.35253715092,2.79199606365,-9.0068673846,-73.4039232214,5.88528556481,16.3898113181,9.68943239478,-0.811402532862,-6.22470653733,0.750971251706,-7.08333200482,18.1019945335,-19.4811994174,-14.6567389019,-7.63778558791,3.13216311679,0.0983037506577,7.24655258262,16.2728338266,1.44781143102,1.4424899326,-3.68058478955,0.607868673939,4.96768382508,-0.398109969154,0.349046691772,0.215213833901,-0.469323812459,-6.26061795486,8.47632944345,1.17671181594,7.14643287324,0.395047043254,0.135121655338,-0.522720079773,0.915046304986,-0.317093453886,-1.1145931195,-1.1181694019,-0.456872000614,0.849978795714,-2.52449901788,0.406749719446,-1.82752118606,1.14730321996,-0.183953951915,1.28508792581,0.604539771075,1.80519467815,1.31102776133,0.207408182828,2.14930465014,-0.281674165981,1.15458934216,-0.447635030983,-0.162222704781,-0.144422251808,-0.490201997687,-0.307656047276,-0.275156936016,-0.492698396813,0.267535350666,-0.243670532431,0.476881193276,0.0918755085411,0.637806586726,0.301607043571,1.45006209823,0.98783307992,0.483894259338,0.59424152616,-0.401293061619,0.0245061369707,0.00195157089419,-0.161247725943,0.113535724021],[-32613.440677,-1055.73669227,-953.22324949,-2899.66386604,-975.63268238,163.852860216,1355.71926845,312.382171429,-526.038590823,-509.944990867,272.200000296,-28.529144807,-665.131465416,-1532.86422101,-711.850109608,-14.6703146724,-438.705576038,-170.545780796,-606.529461353,191.691267127,-7.60033392869,54.5784954566,69.9019944086,-564.11938874,96.7363206347,-73.0188719828,63.0645195065,41.0284078429,0.746270361094,314.377525023,-26.1764291627,-140.925239128,-109.938498133,88.7089599535,139.563539572,34.1425949598,32.8134826888,88.3181634687,13.4184322788,-12.8533434316,-9.191977195,-20.4887285163,-40.4945401896,-21.5347565694,-1.24376913846,2.69633646237,-9.54312536231,-72.1431848957,5.42865391204,16.7957065402,10.163639722,-0.607032731164,-5.88961929545,1.12586564396,-6.45210606166,17.1812338033,-19.7819841276,-14.4452545498,-7.24748293278,3.35762515184,-0.0126890814622,7.33520915962,16.6226016077,1.39336728895,1.47774654688,-3.59693035425,0.875410896302,4.9483688004,-0.265899826592,0.479711565786,0.0481848634733,-0.614453945667,-6.19122071444,8.3901012683,1.31903566341,7.09881919969,0.478411742223,0.443396194104,-0.435745897295,0.999044192585,-0.305278996227,-1.14834277898,-1.12578198286,-0.385735541188,0.809175168204,-2.4686262149,0.431285324327,-1.83385963404,1.12838471164,-0.241987653196,1.28111312577,0.648695702859,1.8289671281,1.35062540197,0.294118031897,2.14273593922,-0.244177259742,1.13006762386,-0.454397606382,-0.144952889646,-0.169028065271,-0.503642270178,-0.297978357944,-0.274190791708,-0.491481105602,0.26545627927,-0.248919544202,0.486496798839,0.0651212058135,0.634602643272,0.309098479975,1.45114454294,0.990588411382,0.490678307861,0.593823440653,-0.381456291007,0.025668825664,0.00403755612143,-0.166191528757,0.11474565342],[-32584.5634775,-982.917887132,-1015.1806327,-2909.03506926,-975.105213291,119.885847327,1367.72867774,333.376940899,-463.827124091,-530.394649731,289.252930512,-36.0520189573,-655.540865594,-1544.21104841,-729.446253767,-7.45053335285,-450.720967528,-168.531259701,-594.488525869,189.028533968,-31.7485157696,34.4707019763,76.8842648397,-568.635791847,92.5903935878,-75.5527554496,61.4820080723,35.6105952171,-2.39127189301,305.190744322,-33.4185013098,-136.574465101,-109.863483922,91.601869266,134.673205,30.7458482887,34.2670352624,86.6660906375,11.8904258087,-13.1723617672,-8.41753139376,-19.8486293846,-41.1173135515,-22.7529213653,-0.242886126935,2.50710935298,-10.2579757095,-70.7289468865,4.98747281205,17.1832593626,10.6464056507,-0.476508318712,-5.56087570203,1.49815450019,-5.80542504714,16.1964608024,-20.0320628762,-14.2297888557,-6.82892011893,3.53008363931,-0.113797062547,7.47881207606,17.0062963441,1.34976194275,1.5242485183,-3.49363424819,1.12898513553,4.92268055448,-0.128756706843,0.612561916288,-0.123092125231,-0.7575011534,-6.11461019683,8.31457601374,1.4546857101,7.03981396169,0.572613759587,0.763456132028,-0.340977284948,1.06979018448,-0.287976832131,-1.17592111748,-1.12762809742,-0.313210430018,0.767206264748,-2.41348507124,0.45490689128,-1.83677372906,1.10574585136,-0.299054947474,1.27940980887,0.693856584788,1.84771993572,1.38920446414,0.380586629819,2.13781270074,-0.211607688894,1.10096892207,-0.463816286108,-0.126813639355,-0.192023297155,-0.517062013947,-0.287126976491,-0.272814382229,-0.491029169042,0.262186662096,-0.252882394789,0.495257745256,0.0383276314457,0.630944693517,0.317262240121,1.45133492094,0.991784524391,0.496341682674,0.593556083252,-0.362342963667,0.0257172923366,0.004885162558,-0.171747392745,0.116974434569],[-32547.8547117,-904.802694503,-1077.62914044,-2918.1223092,-969.659908684,82.977462336,1375.51766583,355.977436895,-402.793160662,-549.010551908,307.221295694,-42.1326946737,-645.899467507,-1553.5432654,-743.667349669,0.579799684881,-463.075758849,-166.691523237,-581.2377652,184.800360395,-56.3589277581,14.4382004586,84.8401305206,-573.228886902,88.7230899499,-78.4676084818,58.9598033112,30.3118216585,-5.8587697668,295.407043472,-40.841418195,-132.210201271,-109.353147228,94.0468002267,129.356114323,27.3852687974,35.5396499274,84.817242335,10.1431895269,-13.5469108286,-7.75344966025,-19.2760517826,-41.9323626545,-23.7468170571,0.645797418414,2.22361987235,-11.1186875095,-69.1429411885,4.56254577677,17.5443039327,11.1326640591,-0.415677929871,-5.24144556984,1.8540384014,-5.15448506779,15.1504819719,-20.2218476939,-14.0096683069,-6.38405130225,3.6538008942,-0.187851427094,7.67417543423,17.4178425668,1.31516112735,1.57997649476,-3.37125616708,1.36666878173,4.89030750558,0.00998137430947,0.746232071143,-0.297717008238,-0.895788071036,-6.0317591829,8.2500374748,1.58399741839,6.97337920164,0.677272799282,1.09069120653,-0.239582541096,1.12640597448,-0.266123699317,-1.19753601019,-1.12354255509,-0.23985582275,0.724180043024,-2.35903303729,0.477623924935,-1.8362173073,1.07977462864,-0.354766501022,1.28041603894,0.740097571716,1.86196235186,1.42645411179,0.465885807655,2.13444785883,-0.183859035466,1.06743687985,-0.475233953995,-0.108108116692,-0.213299415901,-0.530284540685,-0.275144749941,-0.271161885493,-0.491031732769,0.257893230377,-0.255443960894,0.503107950818,0.0116709379275,0.626978679318,0.325994622063,1.45051772781,0.991274596371,0.500874823618,0.593385849267,-0.3440314297,0.0244959145524,0.00468078365348,-0.177853529186,0.120194319404],[-32501.7055093,-825.3967601,-1132.44736945,-2928.37148362,-959.949906886,55.1979593779,1377.97819017,377.129945991,-344.110687427,-565.432433854,325.599249619,-47.1631611648,-637.833052749,-1559.96935514,-754.461862434,9.28281578902,-475.056153349,-165.204218455,-566.948766268,178.800331495,-80.9247534051,-5.25620226399,93.4914222166,-577.815043938,85.2449963972,-81.5832844568,55.5245133723,25.1723130608,-9.59905200067,285.068176443,-48.3630476929,-127.981673196,-108.478577947,95.9889560903,123.668359346,24.113304955,36.6281423831,82.7898135018,8.21324369198,-13.948291514,-7.2388596535,-18.802235712,-42.9472558948,-24.5252155565,1.42091155708,1.85094923743,-12.0815326048,-67.3717449215,4.15525845812,17.8696768157,11.6165044278,-0.415986760769,-4.93262798319,2.17675951694,-4.51115196602,14.0486834763,-20.3439440747,-13.7838491212,-5.91664775141,3.73693574031,-0.218363915521,7.91663010085,17.8487691601,1.28716048093,1.64217784394,-3.23186394501,1.58675822039,4.85151208177,0.146166523724,0.879360827771,-0.474750091286,-1.02629747374,-5.94363534043,8.1961257926,1.70808084554,6.90409522369,0.79224398044,1.41986869879,-0.13321426492,1.1683549502,-0.240954939681,-1.21368048876,-1.11363385777,-0.166528964984,0.680278031251,-2.3052384254,0.49966813549,-1.83245933608,1.05115992928,-0.408619568752,1.2845396775,0.78770158879,1.87245144207,1.46235514201,0.549066270448,2.13234490269,-0.160701109263,1.02975046894,-0.487801058416,-0.0891717748156,-0.232784423296,-0.543110645638,-0.262154275458,-0.269392837232,-0.491121436082,0.252839593035,-0.256562872212,0.510092896088,-0.0146237295493,0.622915131242,0.335232357095,1.44860107488,0.989042206815,0.504308577128,0.593245821198,-0.326576697262,0.0218927246907,0.00368212837829,-0.184392437121,0.124334095563],[-32445.7670772,-749.79721721,-1170.12811981,-2940.96754669,-946.882686168,38.2300812593,1373.57207901,393.506692351,-288.870330228,-579.33601043,343.872095169,-51.698407236,-632.93718086,-1562.57815756,-762.094928281,18.4910945617,-485.883565542,-164.147047447,-551.85866164,170.833790935,-104.960151476,-24.4299533373,102.488116029,-582.313282149,82.2660182607,-84.6887026542,51.2499894848,20.2365204263,-13.5485243539,274.223787014,-55.9046541581,-124.027676828,-107.34354791,97.3772724315,117.678069748,20.9834564994,37.5342911855,80.6095124826,6.14713792892,-14.3436952044,-6.91389293749,-18.4575470243,-44.1613481363,-25.1098590806,2.08014505364,1.40087293085,-13.0950304401,-65.4055065521,3.76664988235,18.1489800324,12.0904973235,-0.465734336906,-4.63439343276,2.4472590146,-3.88711658056,12.8983576239,-20.3929215884,-13.5514713316,-5.43134402277,3.79042738673,-0.190544087253,8.20011843451,18.2883099639,1.26267345032,1.70740598889,-3.07902561717,1.78753571731,4.80702646561,0.275098443856,1.0108612312,-0.653331190194,-1.14548015592,-5.85106033894,8.15203169233,1.82869293631,6.83694326523,0.917812188375,1.74534879137,-0.0238914061054,1.19541633266,-0.213933630033,-1.22506809111,-1.09827377429,-0.094395706112,0.635804261587,-2.25203903926,0.521519161096,-1.82602653094,1.02094090722,-0.459952620885,1.29216342964,0.837095567503,1.88009132222,1.49720666995,0.629120795909,2.13091472951,-0.141799926376,0.988296633047,-0.500561984014,-0.0703425327812,-0.250439112943,-0.555309365561,-0.248351216445,-0.267663854119,-0.490878548937,0.247364611323,-0.256263954288,0.516362849346,-0.0402568577609,0.618999195833,0.344944966916,1.44549154546,0.985192965473,0.506690921166,0.593028879649,-0.310014685624,0.0178575927817,0.00218207362461,-0.19119985344,0.129274147205],[-32380.3692874,-681.756317826,-1187.50713047,-2955.88082562,-931.359837017,32.7137354494,1362.34061251,403.637689774,-237.794079226,-590.547824144,361.825253357,-56.1614597525,-632.278731597,-1560.98297577,-766.936346399,28.0495449794,-494.824335218,-163.321058806,-536.27840424,160.769803771,-128.09216055,-42.9276759238,111.472691436,-586.766670888,79.8712789367,-87.5705767685,46.2959364647,15.5310149279,-17.6660416719,262.925050268,-63.3858164409,-120.465153581,-106.110737349,98.1875269883,111.496264079,18.0406802586,38.2656431089,78.3064418283,3.99379847445,-14.7109483014,-6.81205871863,-18.2702878198,-45.559811999,-25.5420533937,2.62871896198,0.897385407164,-14.1084383036,-63.237789216,3.3970750521,18.3728442583,12.5412427898,-0.551185371457,-4.34685486432,2.64809607836,-3.29423323609,11.7092337145,-20.3654146212,-13.3112427667,-4.93072490136,3.82534137189,-0.0887156857249,8.51785368673,18.7229154227,1.2385289036,1.77201813998,-2.91876360645,1.96759270912,4.75849120349,0.392080393778,1.1394888332,-0.833049691069,-1.24856351975,-5.75485882467,8.11700458298,1.94738283424,6.77772333558,1.0542018371,2.06048846666,0.0859289708734,1.207885073,-0.186551015924,-1.23254981158,-1.07812391016,-0.0247361948944,0.591405668267,-2.1994947609,0.543847236621,-1.81779856457,0.990780086257,-0.508093192293,1.30358047099,0.888666613367,1.88604932898,1.53157119009,0.704914325064,2.12945646148,-0.126691835981,0.943627082739,-0.512468216773,-0.051934260182,-0.266272841034,-0.566547457828,-0.23398184156,-0.266075134052,-0.489915924674,0.241914209422,-0.25465742364,0.522185520091,-0.06491438563,0.615455810091,0.355144351735,1.44111147622,0.979951569102,0.508072644548,0.592596445116,-0.294366720294,0.0123716230565,0.000549692547447,-0.198084238988,0.134849894836],[-32307.2333366,-622.895851571,-1185.56622942,-2972.21505209,-914.113212151,37.9982486704,1345.15375092,407.876325158,-191.297845728,-599.096655716,379.471982656,-60.7653234549,-636.191368576,-1554.99122925,-769.400489956,37.8072362896,-501.245872318,-162.2853395,-520.523774159,148.543742028,-150.062857357,-60.6024328844,120.064191901,-591.31227062,78.1289931815,-90.0199195219,40.8829598466,11.0771018756,-21.9413807678,251.227754976,-70.7172896473,-117.371634972,-104.994894093,98.4062758968,105.268394535,15.326637734,38.8353078795,75.9140283277,1.80387964376,-15.0402558266,-6.96053077545,-18.2663930691,-47.1163840043,-25.8794881909,3.06929841243,0.382701595263,-15.07147733,-60.8639185689,3.0468549639,18.5338685276,12.9508973197,-0.657469442095,-4.07133675368,2.76248414718,-2.74505717237,10.4928137907,-20.2600154238,-13.0629302129,-4.41438190067,3.85197363735,0.101301072265,8.86211184168,19.1370165863,1.21149202832,1.83265235351,-2.75913411776,2.1255266794,4.7082836604,0.492396277744,1.26387403994,-1.01391578902,-1.33014905492,-5.65596733226,8.09043208262,2.06512715364,6.73291586313,1.20196641703,2.35843093403,0.193524684248,1.20640161696,-0.16033741178,-1.23706538845,-1.05408298428,0.0410308359189,0.548132117208,-2.14777752328,0.567441083845,-1.80903433367,0.962690218174,-0.552278957341,1.31901570599,0.942669562425,1.89175223456,1.5662737302,0.775261881747,2.12695605965,-0.114856826379,0.896327599345,-0.522404297854,-0.0342606645395,-0.280345721993,-0.576404211372,-0.219326136912,-0.264656328782,-0.487883112048,0.237003907227,-0.251934158561,0.527914419667,-0.0882134706998,0.612476505249,0.365853079006,1.43542360271,0.973643896086,0.508526671431,0.59174200048,-0.279647069656,0.00545660593128,-0.00083226593534,-0.204817361656,0.14085217956],[-32228.5964729,-576.512246385,-1167.01473129,-2989.49371772,-896.104532719,52.7156081688,1323.00972632,407.451765304,-149.752005089,-605.072281319,396.851646323,-65.786042881,-644.450567748,-1544.43413125,-769.774607397,47.6241317261,-504.636256467,-160.486862436,-504.891023858,134.195948743,-170.612687583,-77.3108962145,127.921003101,-596.151608045,77.1002376403,-91.8442640445,35.2627378258,6.91852379449,-26.3814815028,239.200528285,-77.8067358512,-114.775488581,-104.214261269,98.0176850919,99.170470585,12.8837793751,39.2627124908,73.4678310256,-0.368234656393,-15.3317247238,-7.38430286561,-18.4631768836,-48.7916663146,-26.1849063289,3.39381638747,-0.0908362600693,-15.9391481413,-58.2864359402,2.71768097319,18.6267465844,13.3003141849,-0.769965032597,-3.80979546105,2.77323763187,-2.25110993312,9.26199706422,-20.0784689309,-12.8094416265,-3.87911168465,3.88042127902,0.390879428478,9.22616259912,19.5153869707,1.17827453316,1.88620012568,-2.6090056637,2.25972222153,4.65905794851,0.5711244067,1.38242987247,-1.19645165639,-1.38522886141,-5.55516880527,8.07215838053,2.18252605804,6.70894033654,1.36184446654,2.63318282618,0.295613709988,1.19207279622,-0.136935150444,-1.23954323157,-1.02721532692,0.101363112738,0.507187248,-2.09714292961,0.593080774983,-1.80125986798,0.938722915426,-0.591536966404,1.33860861784,0.999083818619,1.89878311327,1.60238459679,0.839252076408,2.12208957168,-0.105772417057,0.84700696873,-0.529427812786,-0.0176419720725,-0.292726341204,-0.584451872445,-0.204688260717,-0.263374021306,-0.48443375171,0.233152554351,-0.248355820956,0.533925320554,-0.109687874477,0.610200894655,0.377060647281,1.42847487333,0.966689511909,0.508177060396,0.590128940139,-0.265856425345,-0.00283791747746,-0.00161390859044,-0.21113631858,0.147078758546],[-32147.5362773,-544.190028955,-1136.70019773,-3007.39671398,-878.133598136,74.6484529339,1296.56203372,403.925473383,-113.444639548,-608.717368416,414.092174379,-71.3273219122,-656.419166852,-1529.10479934,-768.281076577,57.3508829846,-504.627576161,-157.298837685,-489.616475268,117.823008816,-189.533089931,-92.913113263,134.763987123,-601.462529283,76.833304226,-92.8766561283,29.6898477253,3.10668674111,-31.005120986,226.930497144,-84.5585619544,-112.650135631,-103.983721198,97.0202926557,93.3760408039,10.7508250841,39.5690458255,71.0030115846,-2.47230078293,-15.5917695275,-8.10009984388,-18.8729633476,-50.5373959315,-26.5229726558,3.59283228972,-0.46127233486,-16.6715403696,-55.5133061211,2.41127037499,18.6481384343,13.5708212493,-0.875553948049,-3.5651221372,2.66449522973,-1.82287026337,8.03073958381,-19.8248146837,-12.5541330109,-3.31936038853,3.9191081777,0.787250669458,9.60270781998,19.8442944847,1.13578963826,1.93015323687,-2.47740816317,2.3685248792,4.61347188478,0.623553058031,1.4936478019,-1.38117737884,-1.40950785918,-5.45308360092,8.06246838354,2.2997914845,6.71202017483,1.5347516535,2.87994027364,0.389158032825,1.16641512431,-0.117873594539,-1.24087617199,-0.998649993716,0.154769085699,0.469867447182,-2.04794159277,0.621460093569,-1.79610309312,0.920774927065,-0.624826584585,1.36242790871,1.05777015405,1.90883479923,1.64101232688,0.896209149076,2.11334964868,-0.0988148294031,0.796269844242,-0.53270983847,-0.00237878906917,-0.303501875051,-0.590288674421,-0.190350147699,-0.262152997804,-0.479269053455,0.230825454221,-0.24423000417,0.540592681826,-0.128839867746,0.608705769427,0.388735749818,1.42038671797,0.959540800575,0.507186839395,0.587369598745,-0.252950945861,-0.0124127736139,-0.00151389597433,-0.216781192015,0.153307234182],[-32067.5837075,-523.841825709,-1105.09343641,-3026.30550423,-860.499600105,101.234377042,1265.79284008,398.42617794,-82.6251985376,-610.446120964,431.630960918,-77.2056762805,-671.451285099,-1509.09702212,-764.733538262,66.8902396552,-501.001829906,-152.092255154,-474.748839274,99.5414219442,-206.690350873,-107.256063278,140.492034433,-607.316331572,77.3728652881,-92.9806349974,24.3717107031,-0.289640013248,-35.8259362176,214.526814588,-90.9076489262,-110.928041937,-104.480804964,95.4447374623,88.0134203379,8.95578240318,39.7738134444,68.5456753849,-4.47188285239,-15.8289730791,-9.11092268735,-19.5121385714,-52.3083858686,-26.9561321098,3.66747190269,-0.670906147533,-17.2455039656,-52.5639800545,2.12716329837,18.5962852421,13.7468290886,-0.965891765817,-3.34128674789,2.42406722388,-1.46898217478,6.81150582024,-19.5055650339,-12.2984362706,-2.7270574866,3.97276596245,1.29287631235,9.98257738465,20.1147731277,1.08142782344,1.96269098198,-2.37195149897,2.45047031908,4.57372900342,0.645647791817,1.59679652471,-1.56820996664,-1.3998285508,-5.35027106961,8.0627258134,2.41707484112,6.74772360184,1.72086422683,3.09545324031,0.472280136508,1.13152818424,-0.104305640732,-1.2418832325,-0.96936379605,0.200127302136,0.437408683551,-2.00064169242,0.65311423638,-1.7949161458,0.910415266765,-0.651213675847,1.39049401313,1.11874843008,1.9236100578,1.68309655955,0.945613194032,2.09950940998,-0.0931216047154,0.744872789348,-0.53181025396,0.0112823655521,-0.312774160133,-0.59360526659,-0.176520475128,-0.260905625845,-0.472173424166,0.230357588429,-0.239848844775,0.548252942859,-0.145200142984,0.607970932394,0.400844550892,1.41136195486,0.952633494457,0.505701403397,0.583086880613,-0.240810104771,-0.0231032296285,-0.000378924220817,-0.221587623852,0.159278563834],[-31992.5656256,-512.858891635,-1082.37957362,-3046.62992461,-843.377743048,129.757631445,1231.08173242,391.407698946,-57.5090137725,-610.783399664,449.791668307,-83.0626676905,-688.968192278,-1484.70175463,-758.828853892,76.1457592522,-493.706518399,-144.361566877,-460.23819878,79.4795030123,-222.010361967,-120.207974822,145.074223695,-613.738818978,78.7417020054,-92.0588681004,19.4648745599,-3.20909936875,-40.8546605704,202.109803369,-96.8112888673,-109.526903212,-105.841753488,93.3436595443,83.1817385142,7.51888658575,39.8934339614,66.1182243514,-6.34309031223,-16.0541105785,-10.4068817057,-20.3963620697,-54.0633344214,-27.5410811078,3.625574481,-0.670223955517,-17.6487457689,-49.4643668445,1.8648925233,18.4709715175,13.8171843257,-1.03615764287,-3.14261218653,2.04432671303,-1.19761768008,5.61634721361,-19.1293897866,-12.0420728645,-2.09430462136,4.04387684492,1.90585324269,10.356165042,20.3207024633,1.01329519011,1.9826384013,-2.29857024295,2.50445514656,4.54136643693,0.634319688889,1.69125340146,-1.75701464145,-1.35453181728,-5.24687037463,8.07446140427,2.53417882329,6.82038804724,1.91951034414,3.27755103586,0.543862663701,1.08986626251,-0.0970483198267,-1.24323104766,-0.940189936948,0.23664359463,0.410878281278,-1.95580864661,0.688392048648,-1.79871639756,0.908723373255,-0.669891785601,1.42274109699,1.18204092557,1.94460427572,1.72931048636,0.987062862694,2.07966304555,-0.0877520804596,0.693570230394,-0.526574014329,0.0231475232727,-0.320641169032,-0.594176512241,-0.163345180372,-0.259542165645,-0.463035623831,0.231985331166,-0.235488550624,0.55716039819,-0.158365598313,0.607918228124,0.413371976062,1.40165189931,0.946339811623,0.503855220349,0.576976604257,-0.229258034816,-0.0347065442255,0.00185085679891,-0.225457980669,0.164744160713],[-31925.4065029,-509.133091813,-1075.01174153,-3068.78542164,-826.92255718,157.971636722,1193.36694801,382.975720047,-38.4399723865,-610.261493913,468.582710111,-88.6546093769,-708.361097048,-1456.32610715,-750.153525866,84.9710853571,-482.88072094,-133.770184946,-446.05489068,57.8503471878,-235.421569649,-131.634647188,148.470705047,-620.785715882,80.9226478399,-90.0664904729,15.0868922927,-5.60910411524,-46.0880727147,189.803649462,-102.241546557,-108.379917496,-108.160668107,90.7875920855,78.9773717729,6.45312929044,39.9415092615,63.7436726594,-8.07317473852,-16.282259689,-11.9703120946,-21.5353053768,-55.7641304771,-28.3242100072,3.47884678794,-0.419265390794,-17.8764811998,-46.2482635381,1.6262837872,18.2735441086,13.7751768084,-1.08461442919,-2.97326003657,1.52166235912,-1.01623872334,4.4574527477,-18.7068231377,-11.7850095552,-1.41497558666,4.13420638595,2.6202036968,10.7148078183,20.4579435746,0.930551445448,1.98912676054,-2.26152903298,2.52968964204,4.51710659539,0.587316601118,1.77597519581,-1.94651430683,-1.2733598617,-5.14264858245,8.09888573435,2.65064932736,6.93264398925,2.12893191308,3.42478707411,0.60322882933,1.04415714755,-0.0966280159906,-1.24540780252,-0.911885898292,0.263801179511,0.391054743363,-1.91414464487,0.727441691586,-1.80815562617,0.91631244272,-0.680220833192,1.45893429025,1.24748337194,1.97297669658,1.77998093764,1.02030734644,2.05332231852,-0.0818111077624,0.643048975793,-0.517060104712,0.0330732666361,-0.32715633951,-0.591878795112,-0.150924916564,-0.257965668693,-0.451852148411,0.235870917252,-0.23141696345,0.567461863411,-0.168046403757,0.608435227811,0.426313487811,1.3915356744,0.940969118554,0.501750866922,0.568837417488,-0.218101137569,-0.0470190010885,0.00519736492541,-0.228318029942,0.169513823647],[-31867.4125367,-508.524170411,-1086.73151381,-3093.26085898,-810.772331525,184.252033889,1153.96601071,372.972793049,-25.9104378278,-609.360985361,487.738550414,-93.7137421175,-728.992753876,-1424.35306908,-738.339574258,93.1425643215,-468.817871118,-120.162648204,-432.147730149,34.9277345518,-246.822667005,-141.446102939,150.635405346,-628.497008988,83.8611612678,-87.0093437771,11.3077837681,-7.45822195657,-51.5066137499,177.735264723,-107.191220915,-107.441315924,-111.486414189,87.8648078641,75.4869457369,5.76312191712,39.9261163741,61.4430879128,-9.65929753522,-16.5307273814,-13.7755630061,-22.9358339832,-57.3795920045,-29.3404635633,3.24392143118,0.112129172168,-17.9288468977,-42.9574050681,1.41466479426,18.0060162577,13.6187453305,-1.11240360481,-2.83772836207,0.856321671518,-0.931303189176,3.34650559912,-18.2495853395,-11.5268076928,-0.684575956419,4.24513817829,3.42524728903,11.0505699775,20.5250904152,0.833420225521,1.98162474618,-2.26333738972,2.52560489791,4.50083425253,0.503349070547,1.84982379634,-2.13502171632,-1.15745039291,-5.03716296725,8.13679833666,2.76609622061,7.08504507885,2.34649993834,3.53654810672,0.650258575834,0.997168922851,-0.10321464443,-1.24873927131,-0.885068451962,0.281343706643,0.378420149693,-1.87640429223,0.77021071333,-1.82349820518,0.933275901627,-0.681703759929,1.49871093664,1.3148942188,2.00944853928,1.83509754875,1.04518690772,2.02041305928,-0.0744751612799,0.59393118694,-0.503472366342,0.0409720876498,-0.332329700989,-0.586690691691,-0.139311695771,-0.256086889972,-0.438711973196,0.24207766215,-0.227866101277,0.579199009843,-0.174047936383,0.609381323832,0.439687048651,1.38128483522,0.936748769397,0.499441852324,0.55857390675,-0.207141573353,-0.0598269454667,0.00963912959421,-0.230123082019,0.17344783746],[-31819.2691385,-507.448278571,-1116.41191066,-3119.67654767,-794.67022857,207.647569254,1114.29344961,360.984292831,-20.100337811,-608.65499903,506.797857695,-97.8835741122,-750.308745923,-1389.17639492,-723.480246274,100.422153605,-451.88703795,-103.575604904,-418.461720171,10.9959417551,-256.172457963,-149.72494254,151.464547522,-636.840118942,87.465596611,-82.9146463306,8.14538518541,-8.74872359803,-57.0682083876,166.022027756,-111.684133606,-106.696376863,-115.829606783,84.6810616063,72.7681586206,5.43944433018,39.8528467108,59.2347857661,-11.1086202272,-16.8082690361,-15.7903624871,-24.6002560801,-58.8896370947,-30.6163141975,2.94721372086,0.943733637285,-17.8084033044,-39.6417286186,1.23190562879,17.6707897876,13.3506976753,-1.12218420909,-2.73955526848,0.052990623944,-0.945661850148,2.29350155609,-17.77033219,-11.2644760715,0.0983384906131,4.37799991178,4.3036319916,11.3556236789,20.5231875129,0.722934326378,1.95995881195,-2.30473506996,2.49223377511,4.49170787094,0.382324980707,1.91246579628,-2.32040472425,-1.009359069,-4.92980484088,8.18822831223,2.88062839088,7.27558139731,2.56929713392,3.61317673907,0.68563443705,0.951321037893,-0.116530715568,-1.25348959914,-0.860176364126,0.289321159793,0.373087554474,-1.84325844809,0.81653800573,-1.84469599647,0.959197158641,-0.674133117101,1.54156751243,1.38426508853,2.05413867092,1.89437816893,1.06164480068,1.98124034506,-0.0649770031154,0.546793515659,-0.486092457423,0.0468486128359,-0.336180326563,-0.578682399881,-0.128501082177,-0.253874615855,-0.423793040738,0.250546489489,-0.225017184809,0.592335731054,-0.176306069337,0.610609870047,0.453537756648,1.3711210971,0.933828987196,0.496935021969,0.546250103386,-0.196151301537,-0.0728683230412,0.0151002714749,-0.230856861576,0.17642883234],[-31781.2397549,-504.099428243,-1158.91389557,-3146.8000666,-778.690969718,228.198648104,1075.8499615,346.57433285,-20.7767215756,-608.831763556,525.278597224,-100.800795154,-771.916692035,-1351.36570675,-706.039418464,106.603595622,-432.493707095,-84.2141752938,-404.929662367,-13.6520442169,-263.491662768,-156.723063654,150.8482296,-645.724720734,91.612489822,-77.8253125862,5.5739817231,-9.49131587106,-62.7082573053,154.765633101,-115.782641266,-106.160407634,-121.158999981,81.3456273784,70.8512892421,5.45648267207,39.7266366064,57.1311108795,-12.436908396,-17.1140355483,-17.9771818355,-26.5279023944,-60.2846214446,-32.1685327954,2.62259734248,2.08281272959,-17.5218416452,-36.3581380702,1.07749266493,17.2705607255,12.9774011145,-1.11846242768,-2.6810546398,-0.878747493933,-1.05787386869,1.30553125909,-17.2816351683,-10.9929737059,0.933204837684,4.53392624864,5.23337649896,11.6226607807,20.45572949,0.600808723541,1.9241267244,-2.38480906101,2.43008826751,4.48825604555,0.225249613159,1.96453873788,-2.50050743256,-0.832818797897,-4.81978230835,8.25279329996,2.99485001278,7.49984649649,2.79399123925,3.65583716442,0.710713951194,0.908659213948,-0.135885575988,-1.25987465866,-0.837461001615,0.28806171996,0.374756022059,-1.81526782447,0.866201719131,-1.87140549268,0.993230694719,-0.657608222286,1.58694146714,1.45574583027,2.1066169082,1.95725466929,1.0697929989,1.9364951272,-0.0525893735502,0.502195173404,-0.465348560375,0.0508121932045,-0.338740645083,-0.567997729578,-0.118434873909,-0.251355378614,-0.40736643213,0.261103560919,-0.222986712159,0.606753451475,-0.174905034523,0.611979925489,0.467927586652,1.36121334582,0.932264630238,0.494193133525,0.53204782885,-0.184870516901,-0.0858568280653,0.021443029391,-0.230544201008,0.178380423268],[-31752.789804,-497.801414562,-1208.79656195,-3173.48883997,-762.925484488,246.415854227,1039.97680287,329.402528159,-27.5483601445,-610.517787077,542.807109527,-102.210429362,-793.434085418,-1311.45049406,-686.528537726,111.502082343,-411.087252367,-62.364667841,-391.457687593,-38.7179009569,-268.778926444,-162.755255215,148.722180948,-655.03044114,96.1613101697,-71.8058680502,3.53989966802,-9.69862283335,-68.3575382697,144.059564743,-119.569570614,-105.852475172,-127.39889114,77.9636547463,69.74514894,5.78007397797,39.5513529188,55.1360801699,-13.6633031027,-17.4444676859,-20.2959570821,-28.7128521963,-61.5610041916,-34.0005174788,2.3035273356,3.52488503585,-17.0817924214,-33.1643854667,0.950162721906,16.8083772157,12.5069351587,-1.10728504127,-2.66387778057,-1.92627030787,-1.26391045459,0.387060827894,-16.7948574936,-10.707352284,1.81845868368,4.71347719603,6.19093551158,11.8458717965,20.3285940053,0.469284400916,1.87433736181,-2.50141534796,2.3400145702,4.48854310236,0.0338070190707,2.00700011526,-2.67342407205,-0.63219629575,-4.7062137677,8.33001084047,3.10957401057,7.75205962191,3.01696424096,3.66668590335,0.727205922941,0.870878804041,-0.160353331867,-1.26799851124,-0.816999896592,0.278082088584,0.382827859147,-1.79287734428,0.918849932112,-1.90304999497,1.03423361432,-0.632425739794,1.6342708677,1.52946771828,2.16612059447,2.02291259607,1.06995919696,1.88710778347,-0.0367394286869,0.460622694669,-0.441814647247,0.053032160614,-0.34003970147,-0.554817530599,-0.109019917893,-0.248576766692,-0.389746436749,0.273492141321,-0.221839501485,0.622243399889,-0.170019822311,0.613349018318,0.48291139927,1.35169949489,0.932007019436,0.491162837037,0.516194979166,-0.173051935476,-0.0985103429265,0.0284952289978,-0.229242701875,0.17927455277],[-31732.6834521,-487.844576227,-1262.86176419,-3198.9860093,-747.47851024,262.967204307,1007.8944897,309.685241887,-40.0590669402,-614.182423393,559.126551675,-101.942935198,-814.370003979,-1269.89266948,-665.414003242,114.941828765,-388.138130044,-38.3539746955,-377.932204681,-63.9147605815,-271.983197411,-168.11739502,145.081233873,-664.606810913,100.970250563,-64.938141281,1.97106847927,-9.37804999664,-73.947823503,133.996150962,-123.129249372,-105.79035512,-134.436680019,74.6257687737,69.4417330655,6.37267720502,39.3296751845,53.2471974414,-14.8054582008,-17.7984653815,-22.7048886664,-31.1433003171,-62.7206793714,-36.1037890885,2.01885272928,5.25375378246,-16.5065863758,-30.1169913831,0.848712906663,16.2880623627,11.9479752033,-1.09490972264,-2.68976178795,-3.07504189758,-1.55854606682,-0.459129946557,-16.3206265706,-10.4044089386,2.75123412473,4.91582453164,7.1529959086,12.0212771308,20.1495741365,0.330889338837,1.81111030841,-2.651622009,2.22326340698,4.4903421665,-0.189673459963,2.04066438299,-2.83762773236,-0.412329062263,-4.58859868712,8.41924650472,3.22551647314,8.02566914666,3.23447230463,3.64847658167,0.736791995669,0.839233584414,-0.188912098527,-1.27788211459,-0.7986935461,0.260029588639,0.396536676916,-1.77643890914,0.973934326127,-1.9388948001,1.08083309926,-0.599045877955,1.68296308711,1.60542655762,2.23159649719,2.09035722516,1.06259779094,1.83414811147,-0.0170311689154,0.422528073878,-0.416152038473,0.0536946217767,-0.340116403642,-0.53933762406,-0.100154405889,-0.24559522793,-0.371254035524,0.287403765405,-0.221582472865,0.638528012328,-0.161873490786,0.614557529157,0.498515014962,1.34268545763,0.932922019646,0.487780672171,0.498933647255,-0.160495401504,-0.110565026171,0.0360733493246,-0.227041559969,0.179123877355],[-31719.9310433,-472.756423003,-1318.70840305,-3222.88095159,-732.469856678,278.374661781,980.303260143,287.911736907,-57.9788888925,-620.154365481,574.043728015,-99.6873418877,-834.071594776,-1226.77289656,-643.045593801,116.74881122,-364.111374514,-12.5159023429,-364.199456652,-88.9836871198,-273.029019182,-173.044105795,139.941252932,-674.248067849,105.899107889,-57.3127942715,0.7778905707,-8.53091176035,-79.4169499105,124.67157786,-126.531565086,-105.970574962,-142.139695351,71.4099651138,69.9067219301,7.19463282593,39.0631811725,51.4557847176,-15.8778259745,-18.1759719211,-25.1570686776,-33.8028158663,-63.7674477946,-38.458178367,1.79135316856,7.25033055842,-15.8172976961,-27.2620035789,0.771983387752,15.7139074292,11.3094834736,-1.08705193843,-2.76031167267,-4.30892806318,-1.93619621397,-1.23118742044,-15.8674685059,-10.0816463186,3.72773324651,5.13801640792,8.09712622895,12.1455530005,19.9273432473,0.188229047179,1.73521840502,-2.83200701306,2.08134742418,4.49110437049,-0.442132197341,2.06611723919,-2.99154319328,-0.178210243145,-4.46659388493,8.51967731279,3.34290799844,8.31413092881,3.44311039513,3.60479640928,0.741424373897,0.814529916452,-0.220481521262,-1.28950104986,-0.782305144458,0.234637117234,0.4149839792,-1.76616644476,1.03074640844,-1.97804335796,1.13147237951,-0.558041081591,1.73249910749,1.68345306521,2.30189859395,2.15840694441,1.04832058788,1.77863269719,0.00677576563995,0.388172813131,-0.388976136955,0.0529913316617,-0.339026092836,-0.521763481803,-0.0917318328615,-0.242479863667,-0.352204055725,0.302491187055,-0.222169625536,0.655289380068,-0.150719492802,0.615457665869,0.514724819636,1.33424600585,0.934784798048,0.484009698237,0.480531527332,-0.147026789702,-0.121781859802,0.0439763244466,-0.224046778898,0.177956941225],[-31713.9676524,-452.091661869,-1376.27203319,-3245.43398104,-717.93998938,292.892058073,956.823462156,263.986976061,-80.994944187,-628.550762178,587.435804926,-95.2968535575,-851.943982649,-1181.99109386,-619.413077574,116.756753879,-339.444538739,14.8375777414,-350.109806191,-113.703893505,-271.847340712,-177.636645501,133.390727032,-683.725365605,110.815942516,-49.0259517112,-0.137353069585,-7.14573078511,-84.7097760969,116.17143186,-129.810599956,-106.354931175,-150.352186087,68.3828953021,71.0731745924,8.20649413236,38.7540437854,49.7485502342,-16.8896139061,-18.575669323,-27.6044329411,-36.6676896742,-64.7033619052,-41.0314226287,1.63611359664,9.48518237636,-15.0393638388,-24.6335977162,0.719015225797,15.0905576418,10.601027882,-1.08773943486,-2.87675931235,-5.61059832336,-2.39106612148,-1.92784437807,-15.4414496492,-9.73794179672,4.74188644475,5.37474033153,9.00357665857,12.2166988877,19.6718320877,0.0438466547519,1.64766728597,-3.03883657032,1.91623254331,4.48817027414,-0.719800221738,2.08342938976,-3.13356648787,0.0653056388666,-4.34018189568,8.63011859029,3.46111323333,8.61141054567,3.63984481071,3.54022759588,0.743194931872,0.797267950563,-0.254010638346,-1.30282800616,-0.767505079923,0.202704778961,0.437148785486,-1.76206946663,1.08839578124,-2.01950492502,1.18449176502,-0.510101839773,1.78243208943,1.76306674569,2.375910336,2.22581231129,1.02798432379,1.72156907834,0.0347395580138,0.357623126016,-0.360891802166,0.0511059694032,-0.336846717211,-0.502322100027,-0.0836575433555,-0.239308496265,-0.332881350507,0.318367134882,-0.223506230085,0.672186325996,-0.136840398123,0.615939255502,0.531450934821,1.32644796032,0.937310579367,0.479877548177,0.46127608517,-0.132521634966,-0.131972030254,0.0520027961048,-0.220390809183,0.175829678511],[-31714.4864432,-429.812700854,-1434.93801377,-3266.70515238,-704.75495247,307.340781528,936.143834652,237.817544593,-108.441863121,-639.515804118,599.220498744,-88.9931659107,-867.461769545,-1135.70677904,-594.274294185,114.904604698,-314.509552121,43.3648974032,-335.637503699,-137.855063325,-268.485248309,-181.9029586,125.545983008,-692.725347042,115.608308474,-40.1560282707,-0.880716751182,-5.22194749218,-89.7607808378,108.541584634,-132.962040473,-106.908511925,-158.874895081,65.6013655105,72.8531657966,9.36600384433,38.4131123672,48.1104548662,-17.8459618575,-18.9887565516,-30.00495996,-39.7029092882,-65.5356151329,-43.7774901697,1.56371419883,11.9183803877,-14.2055969584,-22.259503123,0.687070431034,14.4246632132,9.83349337856,-1.09756424674,-3.03931895944,-6.96145788097,-2.91478016928,-2.55024907412,-15.0466372665,-9.37395494352,5.78560232115,5.61749596153,9.85527885803,12.2335874359,19.3943643789,-0.100173894837,1.54984159296,-3.26786704958,1.73113383468,4.47885125793,-1.01794402393,2.09255630566,-3.26255284399,0.313526163658,-4.21034411506,8.74941654953,3.57832938632,8.91184436443,3.82153752074,3.4601949582,0.744042431268,0.787604028853,-0.288537006144,-1.31790289953,-0.753882050739,0.165302963053,0.461832645489,-1.76382185623,1.14588102897,-2.06228636711,1.23819868221,-0.456264694476,1.83242422052,1.84336076761,2.45253426104,2.29112654811,1.00275852173,1.6640013021,0.0667845498905,0.330871588595,-0.332530381016,0.0482217407664,-0.333736595027,-0.481282498785,-0.0758357096566,-0.236186877346,-0.313506015928,0.334606958688,-0.225426043941,0.688878019745,-0.120601718972,0.61595099689,0.548488767778,1.31937498605,0.940117354706,0.475496492854,0.441462465805,-0.116888067349,-0.141005857574,0.0599561315504,-0.216233963758,0.172816677116],[-31719.7559306,-409.282309996,-1494.48893859,-3286.52615256,-693.43642534,322.412584835,917.390761627,209.421368733,-139.492804483,-653.191698675,609.162722142,-80.9441394419,-880.279151837,-1088.20401126,-567.364364705,111.166241962,-289.659301333,72.6452997769,-320.787616224,-161.259510075,-263.036374112,-185.826626213,116.55847594,-700.867092638,120.165501834,-30.7913079074,-1.56699164787,-2.77357645962,-94.5059655674,101.81512391,-135.963595145,-107.587761475,-167.475216396,63.1195725543,75.1438978102,10.6270132672,38.0515873307,46.5288473286,-18.7538806124,-19.4000647368,-32.3157083356,-42.8682830057,-66.2686152843,-46.6429030212,1.58798532224,14.5015164013,-13.3541099377,-20.1634558394,0.672387518096,13.7239681924,9.02019007816,-1.11598158525,-3.24742241357,-8.34039605138,-3.49728307708,-3.09902165186,-14.6865348151,-8.98888977114,6.84921768744,5.85560297678,10.6368217485,12.196316823,19.107617701,-0.241550783084,1.4436891998,-3.51417003237,1.52988507342,4.46061558203,-1.33102500575,2.09336036259,-3.37720536333,0.561234106221,-4.07813005622,8.87620303655,3.69215764298,9.20974590063,3.98519486702,3.37082561502,0.745845945551,0.785175734112,-0.322994348045,-1.33469494202,-0.740964247513,0.12370042197,0.487737054112,-1.77094985135,1.20209114187,-2.10538506357,1.2907114763,-0.397695382403,1.88214929059,1.92333916118,2.53058671857,2.35285793953,0.974100280415,1.60707286494,0.102715274889,0.307841343102,-0.304520633333,0.0445436685109,-0.329881567002,-0.458978071287,-0.0681527365734,-0.233239422304,-0.294322743377,0.350753137591,-0.227719614955,0.705011536197,-0.102415569469,0.615462853631,0.565617106747,1.31310600916,0.942777409586,0.471047052599,0.421425313891,-0.10005020832,-0.148811085828,0.0676364623732,-0.211756391985,0.169016208682],[-31727.175881,-391.624471768,-1555.10828138,-3304.32430449,-683.973299869,338.694817583,900.285828875,178.322757668,-173.165007788,-669.659835971,616.987141654,-71.08845346,-890.398093104,-1039.87895322,-538.573350705,105.563802366,-265.231410238,102.19908764,-305.525957637,-183.788282675,-255.643660797,-189.417361211,106.638543711,-707.702029118,124.376218439,-21.038462774,-2.31588220124,0.175124695825,-98.8804733042,96.0134865554,-138.801867426,-108.335583852,-175.894390674,60.9925375212,77.8253067306,11.9383176586,37.67836398,44.9925317975,-19.6235168034,-19.787929781,-34.4918587689,-46.124354248,-66.9038026027,-49.5668366565,1.72840128565,17.1807871633,-12.5249246335,-18.3648028957,0.669738867707,12.9970572302,8.17636420299,-1.14290305714,-3.49883479005,-9.72361355658,-4.12737773999,-3.57485739339,-14.364111954,-8.57976705635,7.92237892635,6.07701814538,11.3339259009,12.1057955334,18.8254967057,-0.377808738463,1.33153732155,-3.77209771489,1.31655958499,4.4312715004,-1.65285425698,2.08594059276,-3.47623273556,0.802463461566,-3.94415133342,9.0090254087,3.80009648081,9.49917763034,4.12802964972,3.27882614048,0.750539772148,0.78923256806,-0.356156486477,-1.35308758628,-0.728262546646,0.0793173730019,0.51349614852,-1.78285771174,1.25592948988,-2.1477692746,1.33994200588,-0.335573812318,1.93129675693,2.00210093336,2.60874833156,2.40947395177,0.943698690503,1.55198990447,0.142261152943,0.288373278464,-0.277479595938,0.0403287921767,-0.325475360231,-0.435803878105,-0.0604721374545,-0.230613975475,-0.275612164597,0.366337743784,-0.230150222666,0.720213695825,-0.0827317443887,0.614449949896,0.582652446806,1.30769226165,0.944837127944,0.466745762407,0.401532416181,-0.0819479181715,-0.155358036357,0.074822333252,-0.20716278858,0.164549740603],[-31734.4827085,-377.179789806,-1617.02492216,-3319.37860891,-676.279361252,356.730540692,884.916972981,144.081922088,-208.3664034,-688.944543069,622.457440474,-59.2167295132,-897.972602617,-991.142992722,-508.004830947,98.2090964876,-241.545746525,131.533068616,-289.782558134,-205.336347535,-246.484215361,-192.756054188,96.0073532908,-712.73733527,128.136638662,-11.018638921,-3.2452567985,3.59498652814,-102.822853457,91.1444511143,-141.489927929,-109.095396871,-183.85843452,59.2740980238,80.7657740532,13.2450935269,37.3006014353,43.4910564658,-20.4657851667,-20.1279731037,-36.4892400049,-49.4332640461,-67.4437509592,-52.4841219926,2.00648763499,19.8992850169,-11.7591538855,-16.8792513562,0.672702325977,12.2530915513,7.31828174211,-1.17884183787,-3.78957137336,-11.08585463,-4.79236023748,-3.9795256483,-14.0821052946,-8.1426504146,8.99459606538,6.26979195474,11.9328430597,11.963676424,18.5625108923,-0.506441073967,1.215825386,-4.03537345822,1.09530125971,4.38896792812,-1.97681127307,2.07083913541,-3.55849343556,1.03081279373,-3.8086376013,9.14643932394,3.90010235626,9.77381634817,4.24745537741,3.19124673903,0.760027784726,0.798678603062,-0.386686040253,-1.37286393563,-0.715296405328,0.0336640520277,0.537732010504,-1.79882902809,1.30640764887,-2.18835248788,1.38375723579,-0.271049509611,1.97957663866,2.07895365173,2.68554634833,2.45944302207,0.913361823512,1.49995269311,0.18502854209,0.272257840355,-0.252010903988,0.035888650145,-0.320709220047,-0.412199539388,-0.0526550936343,-0.228464208418,-0.257666062184,0.380908762708,-0.232463150284,0.73411397562,-0.0620092495025,0.612884203909,0.599469418823,1.30314199279,0.945833447498,0.462803886794,0.382158278153,-0.0625547844141,-0.160630509977,0.081292107107,-0.202667228095,0.159549530649],[-31740.1918211,-364.028468707,-1679.31751805,-3330.28377997,-669.938627612,377.337684894,871.215006466,106.914057652,-243.859995276,-710.998618685,625.389886302,-45.1519612698,-903.239542878,-942.464105394,-476.135696232,89.303199996,-218.883246607,160.14014132,-273.483815556,-225.836149969,-235.780223604,-196.016920787,84.8668130806,-715.453225904,131.354211036,-0.856063270672,-4.47266025548,7.45237121221,-106.278458648,87.1966019997,-144.071410046,-109.830205284,-191.086127787,57.9965946179,83.8293531721,14.4890649284,36.9241050634,42.0160892376,-21.2905574955,-20.397706246,-38.2677911441,-52.7618801688,-67.8955770767,-55.3270714366,2.44098815161,22.5982887196,-11.093714838,-15.7209802333,0.673231426987,11.5017327377,6.46257313016,-1.22392949571,-4.11464169767,-12.4017526144,-5.47846106269,-4.31592624389,-13.8422071423,-7.67445296791,10.0550579504,6.42338790897,12.4202325511,11.7718997816,18.3330855407,-0.625256324802,1.09900655929,-4.29740316603,0.870242150584,4.33232063113,-2.29595574838,2.0491493082,-3.62308873596,1.23983600908,-3.67173833738,9.28677670227,3.9908695523,10.0269790378,4.34104212851,3.11488206662,0.776011132829,0.811925532138,-0.413214459104,-1.39379534521,-0.701574418161,-0.0117469825375,0.559197090531,-1.81803725695,1.35270336546,-2.22602551293,1.42002034933,-0.205174227634,2.02668109824,2.15345359992,2.75934409365,2.50126588473,0.884907037619,1.45209872139,0.230491296149,0.259296349409,-0.228641934677,0.0315732066171,-0.315788726018,-0.388617565574,-0.0445775579466,-0.22692616891,-0.240767461406,0.394042564182,-0.234384542648,0.746352391004,-0.0406756993722,0.610739400109,0.615988427731,1.29941594854,0.945295170086,0.459417410418,0.363663209988,-0.0419078437933,-0.164616672887,0.0868443307686,-0.198484971478,0.154151839493],[-31743.9283447,-350.153139961,-1741.19630157,-3335.01566478,-664.257520909,401.358547957,858.594733306,67.80263837,-278.096403116,-735.610780339,625.698341997,-28.8316218499,-906.361449859,-894.369669403,-443.773759581,79.1648795437,-197.473298021,187.552656146,-256.604123029,-245.249166475,-223.821224052,-199.490212507,73.3951359606,-715.360198864,133.951046095,9.32647206236,-6.10947134391,11.71031158,-109.209239916,84.1354128175,-146.619759899,-110.51684924,-197.308231774,57.1713694087,86.8751308161,15.6081962626,36.5547439687,40.5606731637,-22.1071275394,-20.5772490937,-39.7947237412,-56.0817188198,-68.270042902,-58.0279705791,3.04413712995,25.2174403189,-10.5628625862,-14.9010024047,0.660885724164,10.7531950898,5.625313506,-1.27777545899,-4.46823749225,-13.6462213209,-6.17114165277,-4.58777181459,-13.6457436591,-7.17349276036,11.0919305947,6.52854266906,12.7837003069,11.5337361606,18.1510033712,-0.732630913473,0.983670899652,-4.55161507203,0.645505395948,4.26054707975,-2.60295021719,2.02243575747,-3.66937055927,1.42328815671,-3.53362722264,9.42826530824,4.07174789084,10.2518393128,4.40691915275,3.05613202936,0.799877165911,0.826795216581,-0.434367648286,-1.41564271199,-0.686579187384,-0.0554097049131,0.576807395244,-1.83955043818,1.39419758748,-2.2597138635,1.44667626748,-0.138892881979,2.07224232182,2.22535262951,2.82831247698,2.53353633109,0.860088492357,1.40947041837,0.277874873364,0.249277088108,-0.207806525193,0.0277741980983,-0.310930541824,-0.365510728839,-0.0361253845957,-0.226117539277,-0.225182736243,0.405350414748,-0.235614718943,0.756591644159,-0.0191203537622,0.607984467521,0.632176198033,1.29643098908,0.942775101728,0.456763278514,0.346401111438,-0.0201333258188,-0.167315258185,0.0913158980466,-0.19481599738,0.148504174284],[-31747.3824467,-334.576162725,-1800.19376558,-3331.06269147,-658.455533158,429.956873644,846.458582419,28.5579677981,-309.151483344,-762.543162221,623.297853872,-10.3754156677,-907.387153943,-847.657294227,-411.946560158,68.2476861488,-177.52259677,213.32571178,-239.182792413,-263.54834277,-211.003849556,-203.569752073,61.731726055,-712.039755484,135.866628913,19.4041364449,-8.26029999207,16.3257405859,-111.595554255,81.8868685965,-149.235271377,-111.143782539,-202.273605977,56.7885707624,89.7677675222,16.5370771767,36.2007095048,39.1180098532,-22.9261774813,-20.6497394875,-41.0449428508,-59.3670494212,-68.5790290684,-60.5226385549,3.82107686342,27.6940528373,-10.1995758983,-14.4286912844,0.623365958275,10.0184171259,4.82207685881,-1.33966510954,-4.84395404189,-14.794123558,-6.85451433081,-4.79965092883,-13.4939519238,-6.6394403447,12.0929661448,6.57737957551,13.0115031509,11.254384751,18.0286295645,-0.827533158121,0.872611057812,-4.79147448126,0.42509480369,4.17342342075,-2.89000945279,1.99260449989,-3.6969792483,1.57535993772,-3.3943731978,9.56895126566,4.14254072135,10.4413453538,4.44390802544,3.02103434762,0.832636098678,0.840684571881,-0.44884282435,-1.43811044665,-0.669760411377,-0.0958365861622,0.589613000891,-1.86226443844,1.43052194598,-2.28838938858,1.46182494287,-0.0730413713202,2.11587286446,2.2944816405,2.89048896374,2.5551413936,0.840659719182,1.37304966841,0.326193846736,0.241976690681,-0.189903933806,0.0249222472897,-0.306361333235,-0.343325016946,-0.0271823407298,-0.226115189878,-0.211166158114,0.41448856778,-0.235825771518,0.764529863338,0.00229349564369,0.604605258494,0.648033563928,1.29407262684,0.937890803559,0.455020614415,0.330720118606,0.00257508006764,-0.168738392942,0.0945820256021,-0.191823260039,0.142777746224],[-31754.5701834,-316.787844415,-1848.82446592,-3315.09068656,-651.789326113,465.233697541,835.191552934,-9.13573439748,-334.727977256,-791.586100416,618.095187947,10.2324303933,-906.474365986,-803.463086705,-381.991732687,57.1165837141,-159.233766339,236.999264932,-221.282516988,-280.725266095,-197.857652408,-208.747824824,49.9691788195,-705.152034098,137.057892997,29.2500774598,-11.0307182042,21.2391871757,-113.419602229,80.3356041448,-152.043225866,-111.714601518,-205.761748027,56.8271014837,92.3855626064,17.2095810452,35.8712062871,37.6830950161,-23.7643747806,-20.5969132347,-42.0008289169,-62.5967905028,-68.8356319774,-62.7532841829,4.77558330707,29.968224541,-10.0328523436,-14.3123868124,0.547066607199,9.30905690965,4.06848419349,-1.40962054599,-5.23408966319,-15.8207912744,-7.51210970142,-4.95665326995,-13.3882177288,-6.07185297759,13.0459917547,6.56287100714,13.0920753028,10.9401249494,17.9761636306,-0.909520851277,0.768829827119,-5.01052478266,0.212707880538,4.0713202917,-3.14914392229,1.96210581147,-3.70587973911,1.69062624971,-3.2537854709,9.70664490768,4.20309532304,10.5882102026,4.45153208569,3.01480315617,0.874973308892,0.850851368314,-0.455453566691,-1.46087666997,-0.650547078728,-0.13158478051,0.596801108506,-1.88498031633,1.46165158851,-2.31114544616,1.46373253803,-0.00837160631438,2.15717004032,2.36066930399,2.94378551091,2.56529606294,0.828262739641,1.34375099417,0.374401714974,0.237139722211,-0.175301038521,0.023466108187,-0.302310383213,-0.322490243959,-0.0176148748876,-0.226980564143,-0.19896727334,0.421199710409,-0.234696995715,0.769920252433,0.0232015325891,0.600609783866,0.66358809484,1.29218990398,0.930355652479,0.45436208828,0.316981975607,0.0259813191643,-0.168922610063,0.0965167289848,-0.189631646532,0.137155728629],[-31770.3885711,-297.765604315,-1877.21878347,-3284.0252209,-643.713548536,509.280595973,826.72590893,-44.9260115764,-352.727832515,-822.400410634,609.849257163,33.3044579658,-904.015404327,-762.912858788,-355.26369815,46.331880754,-142.786951249,258.131645814,-202.951620265,-296.787408785,-184.930227799,-215.506617408,38.140890277,-694.540368891,137.499545054,38.7400023912,-14.5116311858,26.3785847088,-114.657916966,79.3486849369,-155.172282134,-112.238650548,-207.631818134,57.2752284877,94.62190525,17.5702112226,35.572604144,36.2560843214,-24.6427351044,-20.4003088969,-42.6524041281,-65.7535139043,-69.0509325392,-64.6822796091,5.91390487328,31.9843497381,-10.0860006899,-14.5537898535,0.42101993105,8.6356671204,3.37966938264,-1.48879589768,-5.62999601614,-16.7052883875,-8.12966703907,-5.06305997889,-13.3318531655,-5.46949343815,13.9386567877,6.4794837538,13.0161070388,10.5981152474,17.9998022877,-0.978537893961,0.675133542897,-5.20288025566,0.0114132980393,3.95470026313,-3.37320155373,1.93316193631,-3.69609426288,1.76442448882,-3.11130518032,9.8387034649,4.2531862905,10.6857953009,4.43015220556,3.04100220392,0.927275331981,0.854844322961,-0.453325055937,-1.48352839925,-0.628472543724,-0.161380486618,0.597669981808,-1.90657388049,1.48782023737,-2.32718747703,1.4510822333,0.0544020736382,2.19570575868,2.42365432154,2.98616401749,2.56365674414,0.824072478919,1.32235035769,0.421467937315,0.234420489079,-0.164292521827,0.0237834505185,-0.298951929826,-0.303404533854,-0.00728534924889,-0.22873840255,-0.188783654625,0.425356366927,-0.231966821729,0.772622989204,0.0432319636324,0.596017454246,0.678869849792,1.29056932691,0.920021536862,0.454863628793,0.305541172323,0.0498172888089,-0.167942854665,0.0970131117195,-0.188308082727,0.131808903819],[-31798.416098,-279.86376821,-1881.39685116,-3237.47536897,-633.983600471,562.480329622,823.000379781,-79.0644987096,-362.341122648,-854.485130885,598.160028222,59.1011210317,-900.528198202,-726.387578199,-332.554682367,36.2827825275,-128.289134951,276.428088598,-184.239796868,-311.789042118,-172.524289989,-224.081763324,26.244915475,-680.337637758,137.216292539,47.7619274579,-18.7374868276,31.6750312411,-115.296806273,78.8230026712,-158.707982636,-112.715553839,-207.886067409,58.1088093602,96.3660444529,17.5966538458,35.304053457,34.8472459955,-25.577468499,-20.0481951433,-42.9991845009,-68.8276969488,-69.2269608528,-66.3098814009,7.23587220748,33.6861740091,-10.3751448175,-15.137265369,0.242520545755,8.00600053271,2.76861822762,-1.57769685202,-6.02341227017,-17.4363564288,-8.69996190145,-5.12081401461,-13.3310521065,-4.83293251304,14.7567348074,6.32326690539,12.7821227151,10.2373085197,18.0999141536,-1.03475048629,0.593983390094,-5.3642925425,-0.176700409697,3.82405443626,-3.55775830651,1.90638646722,-3.66753063775,1.79363151113,-2.96649923645,9.96151643152,4.29255006886,10.7301201187,4.38205170382,3.10048039535,0.989622069735,0.850145175157,-0.442256911437,-1.50547781039,-0.603382940294,-0.184385899014,0.591800261876,-1.92623322246,1.50934701385,-2.3359282556,1.42334031585,0.114685281054,2.23103646577,2.48317412169,3.01608965779,2.5507123274,0.828414386668,1.30934608282,0.466216641203,0.233321182461,-0.156955231767,0.0260282214747,-0.296355597972,-0.286420902547,0.00389324688389,-0.23131712485,-0.180697720649,0.427026991835,-0.22749657814,0.772697277704,0.0620915498556,0.590874222448,0.693898906538,1.2889233633,0.906956578725,0.456411065626,0.296703232406,0.0737082889529,-0.165960300257,0.0960428183638,-0.187829339557,0.12686515018],[-31840.100807,-264.404701182,-1866.3443271,-3177.52736949,-622.019274418,622.986600476,824.588947927,-112.205941311,-364.044928399,-887.214774641,582.68499259,87.4876085483,-896.684948065,-693.497904883,-313.900957794,27.1212644616,-115.741194148,291.800286337,-165.243648895,-325.849500484,-160.686162479,-234.349522135,14.3324686683,-662.957492441,136.277108211,56.2290907167,-23.6674621646,37.073801193,-115.335010586,78.6970472662,-162.646646594,-113.111131582,-206.666190315,59.2750897673,97.506183356,17.3022045891,35.0584687654,33.478023348,-26.5719614989,-19.5334670367,-43.0515605334,-71.8129988221,-69.3506415657,-67.6710454775,8.72974265752,35.0173869976,-10.9076867102,-16.0286130656,0.0171142735267,7.4245205688,2.2447875278,-1.67411399922,-6.40735117519,-18.0123975291,-9.22300287211,-5.12818853957,-13.3926817173,-4.16613259528,15.4834230566,6.09094006808,12.3987738771,9.86882099825,18.272299567,-1.0782873477,0.527375151808,-5.49294247236,-0.350299477453,3.6802109577,-3.70129837717,1.88062541504,-3.62005212502,1.77729906409,-2.81960384515,10.0705490213,4.32035743673,10.7209214829,4.31188274444,3.19158542568,1.0616166319,0.833987462703,-0.422710057224,-1.52608205704,-0.575540070133,-0.200342056174,0.579146716805,-1.94348090244,1.52648773459,-2.33716946429,1.38088629108,0.172033569633,2.26271555572,2.53885683294,3.03284373,2.52792619794,0.840890250615,1.30490299116,0.507295878407,0.233187734092,-0.153075101943,0.0301059583242,-0.294505931526,-0.271818660978,0.0159056489898,-0.23455960704,-0.174687512763,0.426444805215,-0.221288512404,0.77040861406,0.0796217025906,0.585295728041,0.708652030948,1.2869728591,0.89149589181,0.458767497374,0.29070264021,0.097141713082,-0.163261552243,0.093671624133,-0.188085518102,0.122420097435],[-31894.7163492,-250.886725697,-1841.61570888,-3107.85859573,-606.746707124,687.691105278,830.148655792,-145.276121247,-359.064277716,-919.866557098,563.367065494,117.819061739,-893.195977389,-663.468041321,-298.572978946,18.8295845757,-105.03619128,304.338954693,-146.107126292,-339.116066778,-149.349188173,-245.837772849,2.51557683787,-642.97377298,134.778979204,64.0832911396,-29.2019385327,42.5430646603,-114.787347313,78.9369315444,-166.893331367,-113.353558766,-204.196036453,60.6911440123,97.9370247552,16.7252806135,34.82697432,32.1734920066,-27.6126692642,-18.8521521358,-42.827312193,-74.7001596227,-69.3969255234,-68.8179057965,10.3692723791,35.9268828309,-11.6865433364,-17.1785021275,-0.24450946095,6.89268050904,1.81361603975,-1.77276422875,-6.77654927003,-18.4377231928,-9.70371944082,-5.08076100655,-13.5213693839,-3.47712060466,16.1014379175,5.77819665518,11.8832909023,9.50468011127,18.5097220735,-1.10926421201,0.476609847345,-5.58920220159,-0.508541355787,3.524426934,-3.80427102548,1.85345585318,-3.55352058776,1.71673590775,-2.6715811957,10.1611335466,4.33475397505,10.6615596836,4.22588779366,3.3111807237,1.1423849997,0.803540691861,-0.39562704845,-1.54478231382,-0.545515386424,-0.209551804038,0.559960028346,-1.95801220427,1.53940457533,-2.33103384036,1.32490449259,0.226165046515,2.29041299501,2.5900808829,3.03660365515,2.49742927074,0.86071331999,1.30882152033,0.543254722327,0.233241020047,-0.152245479174,0.0357574839246,-0.293341781479,-0.259783654372,0.0286172522865,-0.238257777501,-0.17066238592,0.423944178495,-0.213433695731,0.766158879511,0.09581608022,0.57948065604,0.723050874995,1.2845263848,0.874164942928,0.461678877682,0.287674872125,0.119504578179,-0.160236577797,0.0900249782815,-0.188904580923,0.118542263044],[-31960.4692526,-242.353966593,-1816.2692176,-3032.73205958,-588.142368468,753.883177093,836.92338759,-178.343496326,-348.844554225,-951.779494789,540.549290054,148.914121626,-890.477439013,-635.549606726,-285.285417051,11.3615439497,-95.9619281763,314.28266954,-127.03094272,-351.670828612,-138.42468263,-257.821951696,-9.10286123841,-621.044518026,132.846622789,71.311379065,-35.2008724209,48.0704533162,-113.670525203,79.5104241699,-171.28824527,-113.380048951,-200.730835331,62.2467142196,97.5837474275,15.9196675158,34.6077155364,30.9575563368,-28.6699569032,-18.0038160133,-42.3511758498,-77.4738033354,-69.3440752914,-69.8050866684,12.1146422192,36.3764937728,-12.7119796071,-18.5285758818,-0.529267130729,6.41104161574,1.47631117924,-1.86491205758,-7.12733060059,-18.7202569655,-10.1491295073,-4.97534955139,-13.7174769814,-2.77826456955,16.5975452754,5.38021391028,11.2597955939,9.15675000728,18.8025393729,-1.12806944946,0.44226381199,-5.65508843292,-0.650584095959,3.35821105166,-3.86817389831,1.82183592521,-3.46840963698,1.61552647255,-2.52425199545,10.2297358807,4.33311719886,10.5583051728,4.13055126182,3.45496048778,1.23043581449,0.75624051732,-0.362327935494,-1.56122229355,-0.514044309737,-0.212660918183,0.534671627931,-1.96952660059,1.54818493606,-2.31783329421,1.25726655486,0.276860486714,2.31413729708,2.63597450651,3.02834449386,2.46154037901,0.886844891791,1.32055939616,0.572715150558,0.232693818689,-0.153979742636,0.0426183942549,-0.292803586677,-0.250407367058,0.0417978350871,-0.242185518566,-0.168452369715,0.419916643374,-0.204026878497,0.760434297285,0.11077271221,0.573717518108,0.736958228936,1.28151869771,0.855523911605,0.464902383067,0.287606820761,0.140166639401,-0.157337170348,0.0852743337744,-0.190079629056,0.115282412166],[-32035.0967411,-242.281615756,-1797.96529608,-2956.09583159,-566.378108837,819.270269379,842.184485979,-211.393400036,-334.849406396,-982.299906115,514.683001682,179.337593035,-888.908644814,-609.25977102,-272.673830479,4.65087242385,-88.3120654625,321.935533079,-108.253154033,-363.594175152,-127.850952441,-269.525592469,-20.3915887735,-597.880631575,130.601256261,77.913720941,-41.505738625,53.6484710409,-112.014401207,80.3814469667,-175.645517243,-113.116943918,-196.532869223,63.8284454372,96.4046143937,14.9452693078,34.3997394455,29.8536636192,-29.7059810125,-16.9931966493,-41.6493270404,-80.1127643422,-69.1647723411,-70.6871424379,13.9213651535,36.336787422,-13.9808024436,-20.0190938095,-0.82262004713,5.97975458998,1.2309073878,-1.94021409886,-7.45626637523,-18.8691326407,-10.567375833,-4.80810342809,-13.9788591487,-2.08324165302,16.960686276,4.89320402375,10.5556107942,8.83704985748,19.1396266771,-1.13505567292,0.424556579835,-5.69357592213,-0.775799775646,3.18339676494,-3.89500435371,1.7823610704,-3.36571868953,1.47857253444,-2.37948909892,10.2732473444,4.31237574902,10.4188874621,4.03237527876,3.61803480565,1.32357294514,0.690029211366,-0.324264071634,-1.57510764295,-0.481922640504,-0.210581900755,0.503898487625,-1.97781800247,1.55279806434,-2.29814427617,1.1802115863,0.324057946597,2.33401048355,2.67549153428,3.00950209477,2.42273761795,0.918207495019,1.33929988294,0.594389259858,0.230834494491,-0.157752185717,0.0502702732179,-0.292814178265,-0.24368931817,0.0551468662834,-0.246128443198,-0.167866020171,0.414776121789,-0.193222578561,0.753739334413,0.124671123725,0.568330416565,0.750203256282,1.27796672814,0.83616890068,0.468250177898,0.290363676112,0.158499710481,-0.155028172447,0.0796332128365,-0.191375731908,0.112684024852],[-32117.8218397,-248.602690075,-1792.25818339,-2880.79859946,-540.65211515,881.799975901,843.624224964,-244.963187085,-318.257387347,-1010.80203473,486.175061332,207.698604389,-888.973314418,-584.842777485,-259.482787016,-1.34801742222,-81.9831958162,327.609176552,-90.0526367392,-375.026943353,-117.810265647,-280.179364505,-31.1110183189,-574.113747115,128.142953562,83.8734190904,-47.9717165428,59.254341416,-109.863450417,81.4783329234,-179.754379305,-112.433107271,-191.839365134,65.3380234854,94.3623321643,13.8567187682,34.1973761391,28.8823462397,-30.6854611458,-15.8264421664,-40.7465876314,-82.5860974445,-68.8161302474,-71.5116814209,15.7479933632,35.7816748217,-15.4919714089,-21.5945087604,-1.11139554705,5.59941255567,1.07347882889,-1.98838645468,-7.75901708736,-18.8918222881,-10.9653005084,-4.57290084104,-14.3018062676,-1.40453601432,17.1796501257,4.31117822057,9.79666154502,8.55769871518,19.5105413408,-1.1304762649,0.424100703744,-5.70785674365,-0.883734148568,3.00213586416,-3.88628799101,1.73175948234,-3.24691138476,1.31124036419,-2.2389952781,10.2885570018,4.26827924366,10.251214407,3.93834947324,3.79628762316,1.41927551503,0.603231087581,-0.282700566061,-1.58606316944,-0.449862372107,-0.204311173662,0.468392297311,-1.98272921577,1.55305625303,-2.27291705893,1.09602571297,0.367790446213,2.3501541388,2.70726094886,2.98167397975,2.38369524479,0.954087348391,1.36400411002,0.607056817351,0.227062890032,-0.163058377691,0.0583221610805,-0.293295430404,-0.239551747462,0.0683437853461,-0.249923981399,-0.168742969039,0.408886027298,-0.1812705918,0.746551904916,0.137729059077,0.563649554018,0.762555792797,1.27394683734,0.816752908079,0.471684982663,0.295751221437,0.173870582765,-0.153740740515,0.0732860026526,-0.192557553204,0.110782923005],[-32208.7301777,-254.925257768,-1802.55011429,-2808.43985339,-509.27457103,939.960896355,839.387895126,-280.343642498,-299.899131683,-1036.69897498,455.379629634,232.77148568,-891.360255054,-563.131182962,-244.691335308,-6.63332014395,-76.9398431964,331.587596221,-72.7269779696,-386.163165618,-108.654392404,-289.09128548,-40.9206253443,-550.244309086,125.555883696,89.1572104973,-54.4824619485,64.8552404365,-107.269266457,82.7124876507,-183.398560949,-111.157235801,-186.842062487,66.7020807996,91.4113784077,12.6995316891,33.9920965658,28.0586461235,-31.5793281761,-14.508744051,-39.662376906,-84.8568785477,-68.2442024532,-72.3155570768,17.5615928149,34.6845307276,-17.2472009231,-23.2052781828,-1.38488801355,5.27122845953,0.999154052161,-1.99995489799,-8.02995033659,-18.7933175897,-11.3471499265,-4.26239494532,-14.681649659,-0.752158035208,17.2431177103,3.62668001404,9.00656132901,8.33016988049,19.9063057692,-1.11471817019,0.441852276624,-5.70080193433,-0.97406582438,2.81676656654,-3.84303866617,1.66722347627,-3.11361004138,1.11886068275,-2.10413463621,10.2727972142,4.1960016104,10.062724892,3.85531508519,3.98650689323,1.51505027689,0.494589016938,-0.238680486228,-1.59365213016,-0.418414242384,-0.194792337398,0.428885456596,-1.98416040356,1.54875178472,-2.24328015347,1.00688558632,0.408121010587,2.36271225504,2.72978906956,2.94647680799,2.34701330853,0.994147737009,1.39362010393,0.609624955861,0.220924633034,-0.169470215003,0.0664528942084,-0.294180794719,-0.23787081338,0.0810834624361,-0.253474470482,-0.170964299832,0.402544787943,-0.168471781172,0.73930857891,0.150141724739,0.559999298136,0.773761885847,1.26957420701,0.797914909391,0.475289446732,0.303576345542,0.185677413678,-0.153844418065,0.0663730611881,-0.19342269018,0.109600990729],[-32307.9692184,-254.896025693,-1825.76937619,-2739.35414981,-470.756244106,993.917360116,829.006121419,-319.83588148,-280.24878792,-1059.59431847,422.561083535,253.853704472,-897.085305605,-545.377178259,-227.581825192,-11.167492227,-73.151328392,333.988247158,-56.5402815074,-397.174138129,-100.859524913,-295.655723234,-49.4722000158,-526.654800395,122.908957613,93.7217248491,-60.9759673576,70.3952778904,-104.254230131,83.9753015078,-186.36780459,-109.134623862,-181.692604578,67.8948900554,87.5144474967,11.508375331,33.7737726223,27.3900134609,-32.3727758909,-13.0349717511,-38.4130139311,-86.8861659675,-67.3978312521,-73.1235547111,19.3514830724,33.0249951365,-19.2491622683,-24.8095421401,-1.63526486677,4.99630677078,1.00450172502,-1.96874344081,-8.26218380783,-18.5756514035,-11.7138061865,-3.86967532443,-15.1123532877,-0.130248261211,17.1419782672,2.83078641913,8.2054832055,8.16414743266,20.3198455237,-1.08821747312,0.47873283799,-5.6740144568,-1.04670369718,2.62937338182,-3.76567426224,1.58677822022,-2.96710596047,0.906363460834,-1.97556522494,10.223837537,4.09030726188,9.85960157187,3.78920417497,4.18608059383,1.60871489135,0.363471747369,-0.193017026172,-1.59741696112,-0.387846490753,-0.182724082414,0.385788658524,-1.98199910916,1.5397674513,-2.21026917775,0.91471533364,0.445003063143,2.37192239769,2.74154593919,2.90535027281,2.3148869663,1.03826336573,1.42726961227,0.601367218928,0.212034350972,-0.176651478957,0.0744301520638,-0.295396616402,-0.238516665652,0.0931490003295,-0.256788094897,-0.174469000564,0.395979365507,-0.155113869634,0.732368366046,0.161969235319,0.557693536368,0.78356149955,1.26497571116,0.780179862911,0.479203591457,0.313689521228,0.193455386435,-0.155672873554,0.0589545629238,-0.193809987392,0.109148594464],[-32415.466107,-241.667352817,-1850.53333152,-2672.96685124,-423.602521698,1045.61825357,813.783301073,-366.548560011,-259.428487976,-1079.35664671,387.858200037,270.925303836,-907.368171907,-533.179646693,-207.78681572,-14.899921701,-70.6209878888,334.736449408,-41.6722289807,-408.1848606,-95.0347728698,-299.423485154,-56.4837893184,-503.593612519,120.250830443,97.5097990872,-67.4484264417,75.7935692501,-100.818005818,85.1320605,-188.479171326,-106.252032318,-176.492858147,68.9459027111,82.6518397531,10.3073157822,33.5310330906,26.8757379255,-33.0688684458,-11.3898617647,-37.0129372989,-88.6375997828,-66.237462159,-73.9464863371,21.131220716,30.7963148916,-21.499527627,-26.3756482485,-1.85765596672,4.77560306384,1.0887416907,-1.89332466416,-8.44848356088,-18.2383467227,-12.0632231406,-3.39025405324,-15.5859098745,0.464482553847,16.8718626715,1.91483775689,7.40789662472,8.06627425363,20.7458067028,-1.05129495138,0.535776039884,-5.62759703223,-1.10187714655,2.44177539263,-3.65416331084,1.48952582111,-2.80834108288,0.67809326626,-1.85295147553,10.1407451864,3.94613924876,9.64612935197,3.74448742423,4.39303783339,1.69862641977,0.210031308716,-0.146266626311,-1.59684738203,-0.358137467942,-0.168499770288,0.339244978833,-1.97608994567,1.5260851834,-2.17477711856,0.82105751731,0.478284057071,2.37818403506,2.7411896487,2.85942174508,2.28891218313,1.08640369898,1.46425292131,0.582018586147,0.20007411109,-0.184376355168,0.0821110809514,-0.296858342423,-0.24136691149,0.104450192412,-0.259953128882,-0.179268650273,0.389326187961,-0.141451295238,0.725973738177,0.173127485946,0.557020678531,0.791721482583,1.26025658028,0.763895853802,0.483580086954,0.325976119224,0.196946023954,-0.159487014236,0.0510019613442,-0.193601191215,0.109415858494],[-32530.8094001,-209.068428007,-1862.89087856,-2608.21038566,-367.060183332,1097.59092941,795.50417404,-421.779395874,-237.484157135,-1096.22618754,351.462988449,284.455708405,-922.76278629,-527.836211344,-185.422006444,-17.8148364349,-69.4017067454,333.751699224,-28.1911450041,-419.189346354,-91.7211647861,-300.155291915,-61.789183026,-481.225045265,117.607956701,100.459875961,-73.9140956083,80.9709264737,-96.9598611502,86.0665947395,-189.602460142,-102.44871843,-171.329400843,69.899133653,76.8342439756,9.11243212097,33.2533387843,26.5084678901,-33.6802807529,-9.56408642505,-35.4707309799,-90.0813197381,-64.7429793302,-74.7870807661,22.919573067,28.0177573869,-23.9899701306,-27.8797303875,-2.0486916359,4.61011191624,1.25065806352,-1.7760031589,-8.58415220705,-17.7810036011,-12.3903710508,-2.82443263537,-16.0923642834,1.03774103623,16.4365411285,0.87500516582,6.6224089714,8.03910278627,21.1791883449,-1.00397011875,0.613914437444,-5.56132608011,-1.14047770372,2.25550074554,-3.50894895169,1.37587244361,-2.63836049682,0.438329252114,-1.73547082336,10.0243611066,3.76050765055,9.4250242522,3.72411238298,4.60548035417,1.78358111142,0.0350200294045,-0.0987499985749,-1.59144985356,-0.329166239469,-0.152385983992,0.289421113367,-1.96639946806,1.50781581092,-2.13753560616,0.727270874571,0.50788270192,2.38211464213,2.72798646163,2.80959664467,2.27001420151,1.13832396075,1.50375229763,0.551703223045,0.184837106327,-0.192454998181,0.0894130817626,-0.298475311792,-0.246278441151,0.114980456992,-0.26305037626,-0.185421500724,0.382624254065,-0.127686978044,0.720296137913,0.18350375471,0.558210601677,0.79808319369,1.25550075611,0.749215049729,0.488488552284,0.340251115174,0.196069779821,-0.165397478882,0.0424435905128,-0.19271395896,0.110348985876],[-32652.1726268,-156.321931317,-1852.79715308,-2544.79182702,-301.9397207,1151.73459073,776.18033799,-483.484352253,-214.928126376,-1110.60497944,313.686349398,295.387370734,-942.565792893,-529.655775351,-161.044256237,-20.0076004398,-69.5290357967,331.12848903,-16.0156791942,-429.993596982,-91.1278559799,-297.842486428,-65.3869473436,-459.748368348,114.992616317,102.53198445,-80.3612561821,85.8898278696,-92.6954185515,86.7379132674,-189.672124052,-97.7290497225,-166.325629895,70.7935587865,70.1214214263,7.94208216164,32.9312038,26.2774070643,-34.2166253612,-7.5673102372,-33.7860298877,-91.1973255965,-62.9171688274,-75.653566273,24.7278656986,24.7440339378,-26.6952130254,-29.3000917133,-2.20330573496,4.4990528797,1.48521726548,-1.62085828694,-8.6686321799,-17.2069530357,-12.6891388979,-2.178100082,-16.6214202902,1.59397759729,15.8507618133,-0.283160651056,5.85445009228,8.08157602649,21.6130940241,-0.945993296387,0.713246468978,-5.47590947132,-1.16452796082,2.07166780178,-3.33212157489,1.24714453309,-2.45847638391,0.192155014895,-1.62204873123,9.877975077,3.53418534013,9.1983887893,3.72979636606,4.82055359238,1.86235800292,-0.160033760063,-0.0507309268823,-1.58083404668,-0.300898531057,-0.134838867291,0.236728829966,-1.95322319773,1.4852507316,-2.09904858015,0.634958903284,0.53399193345,2.38462485354,2.70219236654,2.75672884908,2.25855553324,1.19316218302,1.5445179479,0.510938894696,0.166282694382,-0.200639966308,0.0962381682881,-0.300117997987,-0.253053612172,0.12473121098,-0.266081301206,-0.192962245859,0.375882194996,-0.113964120807,0.715538448303,0.193068927756,0.561410978845,0.80262956697,1.25074977101,0.736140708564,0.493798067396,0.356142552503,0.190927410989,-0.173321081196,0.0332402958599,-0.191077299742,0.111834057903],[-32777.2527675,-88.0310391216,-1820.86440869,-2483.28516688,-230.323118591,1207.96070885,757.480507203,-547.672865993,-192.622092459,-1122.86394359,274.765950161,304.824131811,-965.371745559,-537.988273106,-135.583947744,-21.6253239447,-70.9881305125,327.167614098,-4.96322612783,-440.387287221,-93.0891113253,-292.755200858,-67.3747244752,-439.467690993,112.414972773,103.722819296,-86.7395258366,90.5745778525,-88.0794660264,87.1826930736,-188.706417399,-92.1352939452,-161.653654087,71.6637309846,62.6178790917,6.81661534424,32.5578037795,26.1727114576,-34.6780102294,-5.42811119883,-31.952846036,-91.9802675302,-60.7750059904,-76.56476833,26.5606338529,21.0527973453,-29.5770820727,-30.6185318749,-2.31537567365,4.43913070622,1.78352785153,-1.43217443882,-8.70406083112,-16.5237138004,-12.9536891305,-1.45982794701,-17.1645757665,2.13723695521,15.1362312873,-1.54461454542,5.10843315901,8.19107207147,22.0395692585,-0.877210863263,0.832671556345,-5.37325829444,-1.177033163,1.8912959768,-3.12712357444,1.10537034411,-2.27024786987,-0.0545973130047,-1.51121743989,9.70655200997,3.27160940623,8.9682123233,3.76241984874,5.03475602794,1.93351610527,-0.373084297683,-0.00246731973935,-1.56482675597,-0.273416591257,-0.116592251669,0.181862139122,-1.93717761047,1.45888807358,-2.05973929499,0.545985146159,0.5571032041,2.38670477115,2.66497945006,2.70163337621,2.2545889276,1.2496378429,1.58501745174,0.460480246384,0.144548696622,-0.208622998827,0.102476977299,-0.301632889998,-0.261451366596,0.133636141888,-0.268989178205,-0.201877779183,0.369108606436,-0.100408797744,0.711944689747,0.20187927029,0.566670590298,0.805484748967,1.24600246483,0.724621120874,0.499238941132,0.373119527947,0.181761106875,-0.183046403398,0.0234491513749,-0.188617453744,0.113730427642],[-32904.2104292,-13.1108948576,-1774.26557629,-2424.14731953,-154.743283423,1264.52854531,740.803168145,-611.239378914,-171.105529094,-1133.2184316,234.733502503,313.791365266,-989.928054345,-551.731241126,-110.281504836,-22.7420204598,-73.702306192,322.263259558,5.14900443773,-450.25331904,-97.269985659,-285.441922156,-67.8914488371,-420.671129451,109.877236293,104.063246127,-92.9790302877,95.0754457245,-83.197117819,87.4733876201,-186.790899204,-85.7071163804,-157.469972203,72.5603305854,54.4414360204,5.74829620874,32.1307808783,26.1842338837,-35.0593918027,-3.17721489975,-29.9621355564,-92.4312308581,-58.3299994275,-77.538557905,28.4227482599,17.0269254069,-32.5957484781,-31.8197645884,-2.38137768728,4.42508206598,2.13518695657,-1.2139532866,-8.69157002694,-15.740368568,-13.1770766229,-0.678365096279,-17.7146413011,2.6734519112,14.3163074702,-2.88931322936,4.38752907898,8.3643116988,22.4507717963,-0.797939886843,0.970077680128,-5.2557394646,-1.18117923312,1.71541697412,-2.89787192329,0.953354224659,-2.0751947327,-0.296149597977,-1.40093853343,9.5156460976,2.9789785844,8.73626443018,3.82211441035,5.2451656374,1.99562492907,-0.601781123151,0.0458903525825,-1.5434693952,-0.246862245538,-0.0984577394086,0.125488183075,-1.91899021421,1.42938243627,-2.02004377667,0.46219536468,0.577793237493,2.38932920621,2.61797578217,2.64510874451,2.25791468965,1.30658254045,1.62368940811,0.401133719967,0.119861899786,-0.216103483994,0.108092799222,-0.302880158092,-0.271218921891,0.141592800393,-0.271753887654,-0.212133062565,0.362295355561,-0.0871711642028,0.709738486745,0.209993780689,0.573980157031,0.806844012968,1.24124844495,0.714550642773,0.504560979824,0.390618627108,0.168912392368,-0.194291701349,0.0132041988037,-0.185261724985,0.115887755754],[-33031.0543234,59.6319042135,-1720.06226532,-2367.50610544,-77.1578650443,1319.2176361,727.336037403,-672.300747477,-150.486825008,-1141.76018346,193.50630821,323.064122022,-1015.27756428,-569.711153321,-86.2675968643,-23.3639777178,-77.5868546524,316.805494754,14.45852702,-459.52368994,-103.315548943,-276.541246189,-67.1044267756,-403.540565883,107.367023906,103.59987625,-99.0097843383,99.4444106208,-78.142124631,87.6850736452,-184.035608977,-78.486854273,-153.860889325,73.5341742119,45.7120376208,4.73967790953,31.6507769426,26.2987644326,-35.3557626875,-0.841371037595,-27.8078181029,-92.5508380603,-55.5960980911,-78.5784200823,30.31573024,12.7454122997,-35.7159191891,-32.8926960998,-2.40056193093,4.45023799726,2.52953204918,-0.970699996896,-8.63150418004,-14.8666173304,-13.3513040481,0.156919874297,-18.2634414044,3.20813473349,13.4132152976,-4.2963205678,3.69337230063,8.59699579904,22.839784059,-0.708663689457,1.122796142,-5.12577010254,-1.17994678108,1.54485741857,-2.64838830137,0.794294411293,-1.87491733916,-0.527134520601,-1.28920856458,9.3107721337,2.66259394499,8.5039527347,3.90787194494,5.44974330248,2.04747784505,-0.843735775842,0.0943326061866,-1.51691979462,-0.221357475335,-0.0811963479347,0.0680924762037,-1.89937216112,1.39737684058,-1.98039584142,0.385149058431,0.596546951243,2.39337510668,2.56278590171,2.58787984426,2.26798452856,1.36312281031,1.65913558216,0.333627410656,0.0924857994498,-0.222872785155,0.113132385526,-0.303729507437,-0.282096770355,0.148511139341,-0.274398433051,-0.223689294974,0.355393696196,-0.074406805751,0.709044097888,0.217443547736,0.583295498031,0.806886991081,1.23648108163,0.705741838788,0.509577897898,0.408110638057,0.152744494051,-0.20675691493,0.0026698648073,-0.18094854497,0.118170260675],[-33156.6423178,123.356545822,-1663.25524017,-2313.95423316,1.33873440809,1370.02075168,717.387542976,-729.539034094,-130.704874054,-1148.53692013,151.096434395,333.036356987,-1040.51804814,-590.755101289,-64.3917638131,-23.4654138622,-82.6026775579,311.192202299,23.0394489581,-468.148271025,-110.897140137,-266.677687611,-65.2022148614,-388.128535231,104.874427201,102.379003453,-104.773868244,103.73351301,-73.0143641708,87.886006827,-180.548052298,-70.5249685023,-150.837746695,74.6260630531,36.5331426498,3.7919611179,31.1181834198,26.4983617353,-35.5625406123,1.55487963926,-25.4891782742,-92.3398515014,-52.5933513074,-79.6719638368,32.2325718797,8.27686100766,-38.907878824,-33.8298439684,-2.37365656809,4.50737246449,2.95553968738,-0.707148242828,-8.52482832279,-13.9129823448,-13.469027345,1.03530139611,-18.8016830839,3.74433215561,12.4461016376,-5.74565606207,3.0259458177,8.88430667058,23.2012608487,-0.609903919448,1.28827139666,-4.98579877658,-1.17612280106,1.38024849913,-2.38266793819,0.631425226646,-1.67119919612,-0.742737478953,-1.17477573098,9.09709107399,2.32831724833,8.27227424872,4.01785752911,5.64728450315,2.08826423364,-1.09682539595,0.142939815212,-1.48535041072,-0.196937987149,-0.0655307050789,0.010075442228,-1.87899828398,1.36344645116,-1.94124162551,0.316051856707,0.613712666408,2.39960934756,2.50093352876,2.53050355152,2.28395409262,1.41857433186,1.69020160552,0.258470862487,0.0627086519184,-0.228783903612,0.117676610999,-0.304054199359,-0.293808046067,0.154317381166,-0.276971277683,-0.236498777478,0.348330385327,-0.0622441593983,0.709893165359,0.224265328165,0.594551407196,0.805779999472,1.23168537829,0.697940954122,0.514144104067,0.425141107687,0.133565194234,-0.220131135415,-0.00798187971448,-0.175641161101,0.12046542929],[-33281.5834133,174.585169372,-1606.66306949,-2264.04943742,80.3440778752,1415.55847389,710.856314328,-782.288286504,-111.659636752,-1153.60958108,107.533530251,343.849096328,-1064.9772225,-613.813151057,-45.4213323966,-22.9947263809,-88.7542625813,305.80244542,30.9060253001,-476.108025838,-119.692088734,-256.461060522,-62.3670806612,-374.328409634,102.394973071,100.440278782,-110.228099941,107.985705175,-67.9088187974,88.1406778308,-176.438600472,-61.8862436714,-148.34039792,75.8575751484,26.9869543827,2.90544057353,30.5312730543,26.7635702337,-35.6784933343,3.98622382813,-23.0084857341,-91.8031040568,-49.3464636628,-80.7931003062,34.1586222255,3.67610957733,-42.1444307942,-34.6295546031,-2.3018854319,4.58950923411,3.40184333374,-0.427953187893,-8.37330833486,-12.8910377286,-13.5242205267,1.94493274354,-19.3200633075,4.28179494887,11.4302149053,-7.21844165352,2.3835870748,9.22024063593,23.5310047002,-0.502168994495,1.46421978403,-4.83825882483,-1.17232557405,1.22189150175,-2.10486404416,0.46762529232,-1.46613699184,-0.939160249962,-1.05734138664,8.87898665821,1.98158241619,8.04153117518,4.14931826857,5.83687773193,2.11750778581,-1.35918557273,0.191854876939,-1.44889823732,-0.173578282414,-0.0521027371336,-0.0482237871428,-1.85858392541,1.32806593146,-1.90303650352,0.255645882044,0.629517226007,2.40862409231,2.4338351904,2.47332386843,2.30469233163,1.47237625719,1.71601507075,0.176017760867,0.0309246688495,-0.233760440394,0.121818330475,-0.303725020566,-0.306062124873,0.158957473498,-0.27952825946,-0.250494069193,0.341020349459,-0.0507897180316,0.71222664205,0.230504316594,0.607647957323,0.803665212715,1.22681689164,0.690829070363,0.518131413822,0.441339496287,0.111598648291,-0.234077469969,-0.0185984153753,-0.169341890989,0.122674044262],[-33408.1647021,213.28291514,-1555.48643561,-2217.96694355,160.188058753,1454.21138809,707.616118718,-831.379960047,-93.2254614449,-1156.96051436,62.652686758,355.510406801,-1088.66388066,-637.989418168,-30.3867571032,-21.8645588735,-96.0502647734,300.981211548,38.0452329751,-483.53767674,-129.356380779,-246.622386242,-58.7549916252,-361.94180834,99.9324283019,97.8206550153,-115.343668472,112.24201024,-62.936219867,88.5140774326,-171.870324948,-52.6506255114,-146.272365996,77.2234269896,17.1274735144,2.07819543345,29.885851192,27.0753762031,-35.7062406569,6.42246537316,-20.3691964496,-90.9629741449,-45.8842225745,-81.9152151487,36.0722445833,-1.02201128619,-45.3992215213,-35.2967122512,-2.18703798244,4.68982645213,3.85691122132,-0.137541825247,-8.1789654479,-11.8134432244,-13.5141326517,2.87279391997,-19.8127645142,4.81692638993,10.3749439109,-8.69635080059,1.76284548833,9.59772009734,23.8252939146,-0.386117948052,1.64856437329,-4.68557072677,-1.17116092656,1.07012045514,-1.8193034621,0.305206827182,-1.26218469109,-1.1143476657,-0.937449174536,8.65917132469,1.62767860226,7.81083006446,4.29859506348,6.01731355716,2.13494479316,-1.62924744913,0.241253632514,-1.40768199811,-0.151182841886,-0.0415101755997,-0.106404012867,-1.83892867562,1.29172318072,-1.86622877618,0.204091464071,0.644122631203,2.42058430567,2.36287631607,2.41621654419,2.32883594238,1.52391116383,1.73597194115,0.0864831054058,-0.00234701941452,-0.23780710003,0.125660665305,-0.302611328275,-0.318561148465,0.162389443898,-0.282104282042,-0.26559245003,0.333416378409,-0.0401155045455,0.715911566433,0.236218664045,0.622393649309,0.800676641699,1.2217026891,0.684028082784,0.521349849521,0.456407470899,0.0869598455728,-0.248243473333,-0.0290526174484,-0.162103313428,0.124706982602],[-33540.1930555,241.746954398,-1510.4897735,-2175.89318106,241.594926204,1485.54907146,706.849319419,-878.179782668,-75.2436273071,-1158.5501993,16.3830144559,367.695392831,-1111.71262275,-662.523136632,-20.1386892908,-19.962115812,-104.517710235,297.078893858,44.3901876742,-490.562390204,-139.547179131,-237.869762581,-54.5007263156,-350.66854777,97.4957255988,94.5573298985,-120.098550225,116.543351277,-58.1940341893,89.0692193581,-167.022775255,-42.9009005748,-144.483305788,78.689417968,6.98854422194,1.30606736924,29.1790820932,27.4122258211,-35.6490827688,8.83228044862,-17.574827762,-89.8478626814,-42.2368511208,-83.0002758321,37.9419534229,-5.79535460967,-48.6464986817,-35.8380743485,-2.03060454093,4.8016988059,4.30853938172,0.1601304234,-7.94382774505,-10.6935677492,-13.4371315504,3.80475245748,-20.2734433496,5.34280113503,9.28665202854,-10.1607667835,1.16003878886,10.0084017287,24.080506127,-0.262520315461,1.83923273796,-4.5303755709,-1.17514486936,0.92500382216,-1.53046568457,0.146177899637,-1.06206264991,-1.26679809347,-0.816030182636,8.43971840408,1.27195841909,7.5789910469,4.46114794158,6.18752848069,2.14072069748,-1.90543763341,0.291285591085,-1.36181203142,-0.129643239915,-0.0343436958515,-0.164125207224,-1.82089491054,1.25494796802,-1.83118260574,0.16123649788,0.65767793291,2.43558768379,2.28938907886,2.3589540312,2.35482014114,1.57271052038,1.74973443327,-0.00996217772202,-0.0365261191968,-0.241039234352,0.129318297107,-0.300570344546,-0.33100694559,0.16457421643,-0.284704964076,-0.281706051144,0.325494323138,-0.0302711002374,0.720760490721,0.241476450633,0.638603030305,0.796946144084,1.21614433815,0.677125435118,0.523624772415,0.470123806244,0.0597177449101,-0.262256413549,-0.0392297752892,-0.154014422443,0.126499695187],[-33681.0066773,263.886884369,-1468.07758277,-2137.58288104,325.627575479,1510.37831723,707.068383013,-924.236529771,-57.4763592978,-1158.21655783,-31.0528193755,379.895994214,-1134.10297615,-686.629920236,-15.3006947422,-17.2056582503,-114.161194852,294.484846092,49.8580756607,-497.217564867,-149.900030179,-230.80924111,-49.6994970122,-340.137679035,95.0872495623,90.6863459957,-124.460562562,120.930654417,-53.7483757642,89.8727795423,-162.060484957,-32.7100969383,-142.780647422,80.1937710187,-3.40298981484,0.581828460635,28.4080739539,27.7505270729,-35.5095861761,11.1854494017,-14.6288422069,-88.4831253961,-38.434836886,-83.9948937545,39.7263922177,-10.6253602837,-51.8566540008,-36.2583350893,-1.83324210099,4.91794036278,4.74371558633,0.461044195154,-7.67027055201,-9.5456932544,-13.2912085696,4.72613457066,-20.692553608,5.84932091883,8.17128786193,-11.5922433645,0.572269262751,10.4427150372,24.2928472932,-0.131920361693,2.0339662225,-4.37581113563,-1.18674577128,0.786369328697,-1.2431981909,-0.00762377828459,-0.868762482005,-1.39480595676,-0.694295811941,8.22262653377,0.919894114318,7.34506429811,4.63184748404,6.34656177862,2.13531259249,-2.18593616998,0.342111143251,-1.3113953065,-0.108909788617,-0.0312315512616,-0.221155534346,-1.80542159225,1.21822711162,-1.7982287418,0.126774091698,0.670338798142,2.45380569148,2.21455638039,2.3013831478,2.38092232126,1.61844649331,1.75713235784,-0.113052708623,-0.071027673368,-0.243621930355,0.13292544287,-0.297429654286,-0.343098523378,0.165474577622,-0.287309142208,-0.298756616307,0.317218111235,-0.0213148371189,0.726521153521,0.246344239439,0.656118662351,0.792568038954,1.20996732477,0.669679355798,0.524833609908,0.482319565694,0.0299406135843,-0.275725847739,-0.0490214206328,-0.145197532175,0.128009616996],[-33827.836691,285.780300309,-1421.12664455,-2101.63785516,414.550960448,1531.09789557,706.297790127,-969.579934018,-39.7666882854,-1155.38535965,-78.8562510456,391.72712667,-1155.08643042,-709.531417529,-16.1601895747,-13.6482608508,-124.900749076,293.67498313,54.4540168272,-503.34103635,-160.074472408,-225.817066695,-44.4547543602,-329.906871978,92.681558131,86.2360204562,-128.393509592,125.459613979,-49.6264983601,90.9867324804,-157.08071884,-22.1618272411,-140.933272732,81.6428206743,-14.0111507237,-0.104779574521,27.5610841242,28.0606718659,-35.2890878257,13.449922345,-11.5361781299,-86.8820084342,-34.5173248665,-84.8262171659,41.3722475501,-15.4834165894,-54.998370494,-36.559648928,-1.59441337043,5.02903904046,5.1470950992,0.760352399323,-7.36417254781,-8.38483526153,-13.0734988467,5.62022737211,-21.0542189086,6.32201532049,7.03904965506,-12.9735111589,-0.00246583156853,10.8897753725,24.4586429458,0.00590208180437,2.23039316398,-4.22568495964,-1.20879307069,0.653247858776,-0.962542432346,-0.154886146771,-0.685803223985,-1.49578458236,-0.574613539201,8.01099969313,0.575930466818,7.10871140786,4.80510841741,6.49349659981,2.11933815826,-2.46881758313,0.394039635265,-1.25646373366,-0.0889074374831,-0.0328908443366,-0.277378561681,-1.79346544766,1.18169017268,-1.76775140842,0.100295987857,0.68207989377,2.47569564524,2.13912878152,2.2435528401,2.40513568899,1.66085387583,1.75793367584,-0.22236537019,-0.105303241562,-0.245712253219,0.136618171557,-0.292960628156,-0.35448702178,0.165071543883,-0.289868893688,-0.316671142849,0.308455198035,-0.0132842342473,0.7328508395,0.250874290615,0.674807740951,0.787500015865,1.20306369189,0.661126296285,0.524907293475,0.492786914771,-0.0022743061019,-0.288271544765,-0.058355796205,-0.135803828647,0.129199924951],[-33977.574287,310.382603134,-1361.98051302,-2066.49054741,509.482062317,1550.62663442,701.423836007,-1013.01989405,-22.0205131119,-1149.71059569,-125.908450394,402.580905143,-1173.59210969,-730.630361845,-22.7349188994,-9.40280214964,-136.594613251,295.14454962,58.178351287,-508.70528364,-169.813094437,-223.10201348,-38.8849215031,-319.578454825,90.2569394469,81.2601781977,-131.853333951,130.19059276,-45.8420069608,92.4468522518,-152.150493494,-11.3647836531,-138.73112641,82.9124392456,-24.7799121435,-0.760934963274,26.6317612357,28.3133847545,-34.9840590185,15.5920517444,-8.31076352011,-85.0600061225,-30.5340605808,-85.4210020592,42.8198019104,-20.3324885963,-58.0363274676,-36.7463178457,-1.31363043007,5.12602333502,5.50240250607,1.05468648845,-7.03411850423,-7.22650243907,-12.7825842252,6.46925669622,-21.3406515465,6.74454709198,5.90213933612,-14.2886477085,-0.566040183642,11.3379540205,24.5745301296,0.151199658005,2.42595672058,-4.08436051328,-1.24370800118,0.52470182183,-0.693201621808,-0.294505040853,-0.516893595694,-1.56686703032,-0.459892414855,7.80820647709,0.243875872467,6.86980840583,4.975295614,6.62706300529,2.0934507901,-2.752009169,0.447288973825,-1.19725967731,-0.0695952153417,-0.0400058801504,-0.332580157199,-1.78578441889,1.14536170376,-1.74013826762,0.0813668145739,0.692882462423,2.50171943259,2.06360304234,2.18552999584,2.42544750222,1.69959575676,1.75191879127,-0.337199996802,-0.138814902105,-0.24746372239,0.140496331968,-0.286978642054,-0.364801704223,0.163342794687,-0.292318436324,-0.335338561662,0.299047815403,-0.00616076877803,0.73938314926,0.255142130597,0.694543985622,0.781618775516,1.1953639874,0.65090378472,0.523809986938,0.501296115063,-0.0367581636859,-0.299546448253,-0.0671995055283,-0.126000645656,0.130052767632],[-34127.7299445,339.634648161,-1286.04492118,-2031.49390735,610.729490743,1571.18371155,689.795539086,-1053.6014188,-4.4116069562,-1141.07652562,-171.090320477,411.992961148,-1188.7231985,-749.143965561,-34.9132221461,-4.63898920967,-149.072449435,299.333491358,61.0840621142,-513.117582603,-178.782484624,-222.785875528,-33.0756964982,-308.842807031,87.8089904983,75.8257245632,-134.785315842,135.183879376,-42.4063438705,94.2939123065,-147.338918004,-0.423119763943,-136.005850914,83.8817994375,-35.6295646208,-1.38581670673,25.6196777733,28.4836896738,-34.5897423761,17.5797052705,-4.97269652037,-83.0410635262,-26.5336828816,-85.7147445635,44.018425024,-25.1286959647,-60.9285483134,-36.8224863686,-0.989759982405,5.20094712593,5.79464871788,1.34064265099,-6.68950687167,-6.08732363632,-12.4197871986,7.25745074022,-21.5350419917,7.10397550146,4.7745835078,-15.5202306005,-1.11868542987,11.776141356,24.637640957,0.304005209221,2.61803344867,-3.95625398359,-1.29360085458,0.400195004405,-0.440040422141,-0.425616726951,-0.36541301798,-1.60536763663,-0.352115260545,7.61772534189,-0.0717951681618,6.6288726832,5.13727685618,6.74588397811,2.05842537274,-3.03306414698,0.501821400596,-1.13417498603,-0.0510034558797,-0.0531919197796,-0.386456512916,-1.78299795653,1.10932257786,-1.71574966361,0.0695740689817,0.702941354431,2.53231318391,1.98861431899,2.12751836517,2.44015315637,1.7343579708,1.73903845844,-0.456476977555,-0.17103534798,-0.248986427377,0.14460319169,-0.279345966173,-0.373694816552,0.160284309249,-0.294573488272,-0.354611209552,0.288879765416,8.76361422893e-05,0.745760057845,0.259238967434,0.715207761693,0.774830815199,1.18685085928,0.638564711226,0.521562612143,0.507666584311,-0.073208097869,-0.309229932911,-0.075506268951,-0.115953402687,0.130574994421],[-34277.5917881,378.247953966,-1195.76986753,-1997.16009474,718.721163966,1593.34158313,671.129148098,-1090.63855518,12.6644549751,-1129.53514154,-213.482199988,420.066505719,-1199.68613419,-764.109246605,-52.3621532984,0.463869156194,-162.241168532,306.627557563,63.3436606374,-516.424094314,-186.5300259,-224.911823248,-27.0444100335,-297.533014187,85.3580791603,69.9808974815,-137.109892664,140.484245017,-39.3326464358,96.5733802733,-142.720653906,10.5785150293,-132.647108849,84.4698237157,-46.4514578594,-1.9695021169,24.5228178042,28.5595874523,-34.1124119819,19.3791672372,-1.54773860169,-80.8590295707,-22.5564503521,-85.661483618,44.9427776599,-29.8229254444,-63.6286028108,-36.788600291,-0.621892597144,5.24684892088,6.01240726751,1.611000643,-6.34130479987,-4.98468551065,-11.9906884356,7.97354814766,-21.6244759724,7.39654099612,3.67317742592,-16.6487831794,-1.65586092538,12.1942060262,24.6461794363,0.463712795843,2.8043906986,-3.84547226607,-1.3608341365,0.279209131777,-0.207918379949,-0.547862830078,-0.233874553993,-1.60925438028,-0.250970009086,7.44333241628,-0.365687675041,6.38797800714,5.28622956979,6.84867929238,2.01522342061,-3.30904476655,0.557270778534,-1.06756520013,-0.0333811311347,-0.0729451822402,-0.438624923123,-1.7855512301,1.0736531895,-1.6948302709,0.0645634095695,0.712830138293,2.5679142266,1.91505853135,2.07015648763,2.44783984355,1.76489864606,1.71959346949,-0.578714491483,-0.201469896532,-0.250326877465,0.148915346229,-0.269934598831,-0.380928891738,0.155961106431,-0.296521529705,-0.374287093242,0.277894289652,0.0054729579467,0.751690382865,0.263247065186,0.736670547208,0.767110785266,1.17761722443,0.623772399776,0.518248220813,0.511824709264,-0.111154785141,-0.317052236025,-0.0831675754325,-0.10583259042,0.130798811265],[-34427.9858395,429.725178174,-1094.21901059,-1964.60339316,833.082254607,1617.4976167,646.513390182,-1122.28770805,28.6191200993,-1115.27907937,-252.297564166,427.133354176,-1205.25639445,-774.552729971,-74.3771679946,5.72548251134,-176.070737157,317.334037866,65.1506274811,-518.40689621,-192.579587289,-229.353637001,-20.8361960579,-285.552451863,82.9340732926,63.7673529812,-138.753745703,146.110710446,-36.619636965,99.3162422931,-138.33765085,21.5417197112,-128.570914509,84.6172100697,-57.1078044708,-2.49736239512,23.3391314469,28.5374321104,-33.5670656205,20.954783652,1.93344211928,-78.5449496194,-18.6447357608,-85.2235095846,45.5781876079,-34.3588499399,-66.09398594,-36.6422127003,-0.209461891693,5.2582162176,6.14719021028,1.8568582286,-6.00168698091,-3.93582360833,-11.502974327,8.60887603045,-21.5984514776,7.62183978555,2.6175622188,-17.6570935871,-2.16992067857,12.5824816751,24.5994577012,0.629267666289,2.98303868936,-3.75544009985,-1.44754328858,0.160899046572,-0.0011881658099,-0.661362326418,-0.123999550044,-1.57703060795,-0.155530046093,7.28909121307,-0.633071503399,6.15022071348,5.41717770826,6.93441708718,1.96469733531,-3.57675007241,0.613112809381,-0.997803277207,-0.0170915160612,-0.0995589923787,-0.488678113528,-1.79373302364,1.03833013156,-1.67740635609,0.0659844035456,0.723178737708,2.60892245935,1.8436495597,2.01437311258,2.4470977417,1.79102632558,1.69400567697,-0.702209638,-0.22972664459,-0.251515476499,0.153365927687,-0.258639170312,-0.386360777074,0.150476045093,-0.298048091919,-0.394119966247,0.266058353662,0.0100179913979,0.756933561835,0.26723193471,0.758770618608,0.75842270139,1.16784753435,0.606204393587,0.513996833607,0.513720501976,-0.150026921598,-0.322816072101,-0.0900589438574,-0.0958137598415,0.130762130632],[-34579.18473,492.183146605,-983.468486397,-1933.95074537,951.943016856,1644.18814966,615.998943456,-1146.43808105,43.0030196183,-1098.48427228,-286.980398877,433.16212683,-1204.13688097,-779.870519736,-100.358028823,10.9561823807,-190.433809784,331.629874421,66.6405042322,-518.842026409,-196.576491714,-235.964907179,-14.5975279405,-272.878543208,80.5426241936,57.2572794373,-139.666077143,152.081555757,-34.2479343993,102.522732505,-134.224447094,32.3340462386,-123.736658879,84.2669599858,-67.4605117127,-2.96372337122,22.0710341164,28.4166711208,-32.9605358007,22.2745887796,5.44319477066,-76.1252429803,-14.8457547059,-84.3759170742,45.909921755,-38.6861154577,-68.2888216789,-36.3893164127,0.246539518664,5.2290871045,6.19271525325,2.0723178005,-5.68205658017,-2.95392355849,-10.9631620092,9.15725237446,-21.4498159146,7.7786840485,1.62492935438,-18.5320500298,-2.65713929469,12.9317629465,24.4969296188,0.799749152335,3.15108540638,-3.68877770072,-1.55528350981,0.0443068602021,0.17724412592,-0.766034912197,-0.0362810496275,-1.50778306655,-0.0652298078841,7.1578869859,-0.87033165684,5.91727026246,5.52531918966,7.00184929876,1.90768821725,-3.83321950481,0.669009782288,-0.925519984771,-0.00249907219412,-0.133323316064,-0.536281674345,-1.80762466905,1.00330991724,-1.66309889041,0.0735166152385,0.734610020907,2.65551964169,1.77483065785,1.96081399014,2.43663965614,1.81236162799,1.66278830015,-0.825329586007,-0.255465311423,-0.25264489376,0.157936578477,-0.245387479121,-0.389896058042,0.143853574797,-0.299066337437,-0.413895712643,0.253320959319,0.0138088543688,0.761297287609,0.271300575573,0.78133408442,0.7487243827,1.15771564373,0.585588212454,0.508882917323,0.513326703283,-0.189286972506,-0.326345336335,-0.0961261198836,-0.0860497397995,0.1304918028],[-34729.8437067,559.90315634,-872.00455804,-1904.00681386,1072.82786289,1671.22977336,578.968711009,-1163.23892987,55.7893247111,-1079.2233837,-317.976428235,438.049731299,-1195.97395189,-779.973481169,-130.114381515,15.9917446748,-205.090838966,349.408539821,67.9428181577,-517.800172945,-198.364781217,-244.793809663,-8.55218138505,-259.618100744,78.1602602298,50.551025801,-139.839594044,158.43090059,-32.2569714293,106.17200607,-130.480904426,42.8241909048,-118.193109103,83.383938581,-77.4002132107,-3.37590960419,20.7264482011,28.2006854348,-32.2891043304,23.3027665086,8.9687137565,-73.6434947192,-11.1970865647,-83.1272068862,45.9328758223,-42.7713387999,-70.1874985882,-36.0462535813,0.742653195126,5.15283498309,6.14784481722,2.25537435467,-5.3934597091,-2.04318046358,-10.3814401665,9.61904118911,-21.1821706645,7.86995686989,0.704410974643,-19.2652599572,-3.12071954198,13.2339428475,24.3376227812,0.97447640379,3.30490629867,-3.64641651923,-1.68484420758,-0.0712832647695,0.327070729429,-0.86266023219,0.0314478271465,-1.40326821218,0.0217088413164,7.04959237755,-1.07469720133,5.68824992755,5.60678742159,7.04960646658,1.84530334306,-4.07592023486,0.724904911553,-0.851575289392,0.0101943097788,-0.174504744181,-0.581055066297,-1.82692647764,0.968456037401,-1.65084186142,0.0863801583896,0.748127271763,2.70710032632,1.70905788387,1.90943089915,2.41557124041,1.82826843603,1.62659411047,-0.946632363376,-0.278441352386,-0.253908746522,0.162684145004,-0.230155907918,-0.391498524457,0.13603190677,-0.299460572036,-0.433473540178,0.239625424551,0.0170512167569,0.76456006199,0.275699082199,0.804033748672,0.738110480311,1.1472380605,0.561819783805,0.502863571398,0.510706313704,-0.228463141536,-0.327477385321,-0.101420958277,-0.0766510736458,0.129999469898],[-34877.6674877,631.429180366,-767.687894973,-1873.66089737,1194.35233065,1695.79045549,536.469379024,-1173.42203955,66.9422214523,-1057.72196087,-346.334637023,442.219993906,-1180.84910628,-775.301486642,-163.280409215,20.6263754149,-219.881918166,370.294331066,69.1883411925,-515.481880528,-198.000068777,-255.819281805,-2.90521766984,-245.867750254,75.745925648,43.7112364264,-139.321135942,165.161603556,-30.7090266905,110.213012703,-127.187696736,52.9100977523,-112.011713687,81.9651417078,-86.8232138383,-3.7445003413,19.3094032188,27.8936537435,-31.5602475158,24.0088089766,12.5013160534,-71.1442884709,-7.72230765188,-81.4990301161,45.6588180674,-46.5845173807,-71.7789216495,-35.6327759762,1.27545356685,5.02386432571,6.01635908916,2.40327518103,-5.14647059946,-1.20257610769,-9.76966745843,9.99929220719,-20.8049481932,7.90401897925,-0.137770489276,-19.8554266122,-3.56611681629,13.4824659441,24.1216230194,1.15340830643,3.44178609633,-3.6275413263,-1.83649811571,-0.186500791795,0.449412604921,-0.953044524407,0.0825578610391,-1.26716384445,0.107855671005,6.96279196214,-1.24526187362,5.46143723897,5.6587866819,7.07708472758,1.7786344764,-4.30258821952,0.780951808039,-0.776630511242,0.021015397216,-0.223084172658,-0.622670664395,-1.85117125162,0.933461734941,-1.63950222893,0.103343732324,0.764714290275,2.7625745805,1.64650726019,1.85988388078,2.38337638878,1.83830756516,1.58611888721,-1.06468809656,-0.298542041812,-0.255575961864,0.167679659076,-0.212944294954,-0.391187649695,0.12699520966,-0.299109929788,-0.452796214896,0.224898573599,0.0199533258789,0.766449614448,0.280646608349,0.826432715805,0.726720589238,1.13636289148,0.534930310827,0.495926013646,0.505976648832,-0.267064003748,-0.326134528707,-0.106082870077,-0.0676977535374,0.129293826353],[-35020.5412455,707.10682251,-674.729364296,-1842.40248035,1315.51661645,1716.01118224,490.423021803,-1176.70003344,76.3003666237,-1034.51934375,-373.092631255,446.270646366,-1158.80402525,-766.851514565,-199.086904826,24.6332322229,-234.724292276,393.778114409,70.4613977854,-512.057153241,-195.74398643,-268.836925704,2.1648719077,-231.766493982,73.2597551687,36.7700876713,-138.188533123,172.245447895,-29.6473714247,114.549064392,-124.376934631,62.5009200296,-105.291458811,80.0262154455,-95.6179101861,-4.07819492175,17.822860605,27.4994016533,-30.7918326707,24.3749697465,16.0244286242,-68.6657819123,-4.43814701755,-79.5224101107,45.113103978,-50.0966524312,-73.066131891,-35.171918077,1.84195370288,4.83836038758,5.80455972347,2.51234026297,-4.95060732026,-0.428938098957,-9.13900073239,10.3049676663,-20.3299443841,7.89261009322,-0.896487491633,-20.3080365827,-3.99878177441,13.6732254596,23.8502663106,1.33693139348,3.56001167853,-3.63034863398,-2.01001461626,-0.301840302708,0.546186184527,-1.03935057188,0.120403452077,-1.10354389097,0.195788791865,6.89583350359,-1.38305767653,5.2350680581,5.67971873089,7.08410738248,1.70858734169,-4.51138879436,0.837340934826,-0.701152397135,0.0301303368199,-0.278750122236,-0.660912378611,-1.87976421339,0.898008895587,-1.62821939031,0.123178711322,0.785102140303,2.82069197859,1.5869635577,1.81174000266,2.33999867455,1.84221295251,1.54213709724,-1.17810566781,-0.315766211087,-0.257965946425,0.172966298791,-0.193781584686,-0.389020633707,0.116790794629,-0.297921166931,-0.471852990178,0.209083880994,0.0226779447149,0.766719789609,0.286260934138,0.848096449938,0.714673003513,1.12504056985,0.505086347035,0.488099170419,0.499289418421,-0.304592142191,-0.322361304728,-0.11029464825,-0.0592292977742,0.12839450216],[-35155.3296231,784.272225004,-597.170521543,-1809.1276012,1434.99913363,1730.58633026,442.724020821,-1173.05586796,84.02050739,-1010.22689081,-399.162941837,450.740305174,-1130.16842993,-755.868271025,-236.631149988,27.891731579,-249.462206679,419.333411303,71.7980130234,-507.720953881,-191.946694384,-283.594801848,6.51550490242,-217.54042719,70.6850243625,29.7855765093,-136.518206486,179.642596756,-29.0891736712,119.05635149,-122.072369939,71.5207607783,-98.1745555957,77.5965989792,-103.673450813,-4.38538138481,16.281089588,27.0275674153,-30.0038367149,24.4031173615,19.5142705944,-66.2475301974,-1.35422865836,-77.2427753295,44.3314653991,-53.2846533071,-74.0610941299,-34.6869688344,2.43694846269,4.59562831843,5.52137466527,2.58048186454,-4.81073898082,0.281392378325,-8.49989677562,10.5447176293,-19.7722580443,7.85049865902,-1.56901841389,-20.6322854366,-4.42297924551,13.8045953993,23.5256460327,1.52460820334,3.6584456148,-3.65242720966,-2.20418469639,-0.416794849738,0.619674593905,-1.12326736166,0.148209630933,-0.916862725716,0.288278450759,6.84645311029,-1.48997981731,5.00759304885,5.66920151644,7.07068999235,1.63587730797,-4.70092612136,0.894020331811,-0.625696492088,0.0376901330165,-0.34084581754,-0.695531228227,-1.91201728225,0.862145771415,-1.61645814978,0.144751028133,0.809877844747,2.8800190524,1.53015603782,1.76450834454,2.28591369742,1.83982348929,1.49549789128,-1.28559500153,-0.33022403111,-0.261391031861,0.178538743861,-0.172813211195,-0.385129375909,0.105516305758,-0.295846548028,-0.490635445478,0.192247443396,0.0253067292541,0.765211584156,0.292574402844,0.868600648295,0.702135508644,1.11319904148,0.472623625097,0.47944610471,0.490834780767,-0.340566908924,-0.316312487467,-0.114237044453,-0.0512503028278,0.127327653392],[-35278.8155184,855.494608935,-539.364145607,-1772.11386134,1550.66171682,1739.06861566,394.15743,-1162.73704568,90.5164842355,-985.428071508,-425.236874233,455.869590489,-1095.58206622,-743.647230728,-275.016787559,30.4049165053,-263.835127236,446.470534555,73.1465435658,-502.69977207,-186.995379583,-299.825150484,10.0382789129,-203.475637137,68.0382334457,22.8559016825,-134.382083186,187.300738544,-29.0128403385,123.59243315,-120.291008699,79.8961941054,-90.8388799848,74.7054650082,-110.901238318,-4.67288990944,14.7078862756,26.4954398321,-29.2154937957,24.1158684235,22.9405120385,-63.9311434755,1.52274319571,-74.717131662,43.354388822,-56.136545767,-74.7806678462,-34.1981993242,3.05283048596,4.29795957249,5.17816239637,2.60832180268,-4.72599981741,0.93116883965,-7.86213849945,10.7280370679,-19.1491453357,7.79362512572,-2.15649746346,-20.8397324538,-4.84094823971,13.8772334879,23.1503337142,1.71502728934,3.7365151585,-3.69089473617,-2.41672543174,-0.529944504172,0.672374373587,-1.20568792031,0.169041901379,-0.711732348705,0.387808521566,6.81166167931,-1.56840901697,4.77770405326,5.62806643915,7.03665979444,1.56106174825,-4.87045121849,0.950744627738,-0.55093297595,0.0437844021501,-0.408400078196,-0.726239756588,-1.9472306224,0.82626989834,-1.60394413886,0.167027625272,0.839458250569,2.93901366871,1.47590402591,1.71759992264,2.22201275719,1.83096907165,1.44709565891,-1.38607157629,-0.342109788372,-0.266054431424,0.184337805802,-0.150289783135,-0.379739143221,0.0932985347573,-0.292913584663,-0.509118257965,0.174576927361,0.027839546093,0.761874047959,0.299550713287,0.887558620276,0.689317618829,1.10072240695,0.438002119551,0.470039727044,0.480848721921,-0.374571024268,-0.308235209479,-0.118057763155,-0.043748239239,0.126118120864],[-35389.2760595,915.598829704,-502.243137014,-1730.30511072,1660.71566089,1742.14099005,344.926722508,-1146.3596897,95.9688400969,-960.693905735,-451.96052937,461.711832374,-1056.00486984,-731.39947011,-313.179189167,32.1977073223,-277.612681838,474.637292942,74.391568567,-497.230204386,-181.250071913,-317.154389735,12.6732947912,-189.825397819,65.3534166313,16.0684772916,-131.870213061,195.143440192,-29.3567894266,128.019981162,-119.024434102,87.565338298,-83.4592536324,71.3737143902,-117.251886009,-4.94360769826,13.1234674551,25.9233662013,-28.4487465069,23.5503428179,26.2740056612,-61.755705612,4.19355217808,-72.0035072622,42.2225363731,-58.6559833752,-75.2468293556,-33.7200902645,3.68255319652,3.94919866146,4.78857531195,2.59748103771,-4.69193856563,1.52322215572,-7.23561710568,10.8657350813,-18.4780591702,7.73655784009,-2.6648248683,-20.9446951337,-5.25192291401,13.8936149635,22.7270289522,1.90680881744,3.79441075123,-3.7420971433,-2.64473604493,-0.640006581258,0.706820981444,-1.28748995179,0.185847448118,-0.492989107728,0.496039248614,6.7877583322,-1.62141152548,4.54470884567,5.55827994343,6.98171562958,1.48470070719,-5.01999739467,1.00725058753,-0.477385065899,0.0485080601587,-0.480249208348,-0.752945690324,-1.9847744829,0.790776848759,-1.59052742526,0.188968132574,0.873953112245,2.99619405131,1.42400255881,1.67048961437,2.14951903687,1.81554187716,1.39786362168,-1.47879882581,-0.351707983026,-0.272015454269,0.190256481712,-0.126469535874,-0.373144316451,0.080284163221,-0.289218462059,-0.527282970095,0.156313594492,0.0302069991248,0.756704770016,0.30708089482,0.904673973535,0.67643566211,1.08747696079,0.401772060326,0.459956828572,0.469617303815,-0.406324107706,-0.29846548667,-0.121854226064,-0.0366892289482,0.124786126488],[-35487.3606318,960.114990395,-485.114478293,-1683.87389891,1763.54808436,1741.0270817,294.984756613,-1124.57426483,100.273509948,-936.614884072,-479.879484687,468.217179538,-1012.59548954,-719.952171069,-350.051120733,33.315002087,-290.600759256,503.260803061,75.3848430753,-491.54231611,-174.956117788,-335.178467058,14.3691109576,-176.817345265,62.6806426361,9.49540360812,-129.079412939,203.070955778,-30.0335307765,132.224649209,-118.253054392,94.4693157069,-76.2052867793,67.6211131046,-122.709041686,-5.19530602517,11.5428561381,25.3329845054,-27.7284915971,22.7550004758,29.4862698234,-59.7569136821,6.66330939771,-69.15976004,40.9768745165,-60.8577411223,-75.4835855243,-33.2614847229,4.31979467252,3.55388097981,4.36736060669,2.54997635972,-4.70165586725,2.05943700989,-6.62990552318,10.9689175466,-17.7755693294,7.69234942859,-3.10316519214,-20.9621010255,-5.65266655227,13.857542499,22.2579508652,2.09867453625,3.83290220433,-3.80195710407,-2.88488919489,-0.746061035047,0.725162751506,-1.36953044971,0.201375736756,-0.265387566844,0.613765460581,6.77065516348,-1.65216441748,4.30852191025,5.462594703,6.90534407589,1.40740704823,-5.1502045691,1.06325573917,-0.405415779755,0.051932306372,-0.555097111137,-0.775790387616,-2.02408055898,0.756006294057,-1.57617268426,0.209605978367,0.913087517267,3.05016800606,1.37428991591,1.62272247316,2.06982691317,1.79343034728,1.34874642389,-1.56332844271,-0.359352818618,-0.279151741832,0.196153045934,-0.101602975299,-0.365679259622,0.0666364619461,-0.284913556222,-0.545101788761,0.13772058834,0.0322852167343,0.749736524868,0.314974288534,0.919732537314,0.663685212249,1.07331245562,0.364508733774,0.449260201112,0.457467346918,-0.435642924919,-0.28738841714,-0.125642847299,-0.030015711013,0.123330921079],[-35574.8519699,985.115822444,-484.445215435,-1634.26269823,1858.04967673,1737.47959671,244.674246304,-1098.16202738,103.030904113,-913.664896284,-509.310855579,475.570540162,-966.518754939,-709.376094996,-384.606959084,33.781991793,-302.631764985,531.783739878,76.0177161185,-485.783877745,-168.161897601,-353.461631413,15.0582217833,-164.611808772,60.0723536799,3.17903835713,-126.107050563,210.96233892,-30.9268731981,136.138315154,-117.936768158,100.556321276,-69.2196942158,63.4685561693,-127.282233289,-5.42186867352,9.9719641006,24.7434994639,-27.0855912803,21.7881926383,32.5515143466,-57.9610351999,8.94010476248,-66.2340943514,39.6554386632,-62.7579483851,-75.5124531654,-32.8232917897,4.95978556739,3.11571847145,3.92938373552,2.46631488859,-4.74688405447,2.5395940898,-6.05294204201,11.0483090229,-17.0546762328,7.67160872322,-3.48084382691,-20.9058119313,-6.03831424912,13.7732213655,21.7441035198,2.28980402084,3.85307345733,-3.86629050637,-3.13389165472,-0.847914366716,0.728487114081,-1.45267079489,0.218318339583,-0.0332263408638,0.741113564824,6.75666012104,-1.66358015322,4.06975589554,5.34428630172,6.80684750347,1.32995232639,-5.26194692475,1.11854510637,-0.335165139397,0.0540812479528,-0.631593616612,-0.795285873852,-2.06472267858,0.722176190709,-1.56088831368,0.228072757478,0.956276697608,3.09982025753,1.32664177023,1.57404453941,1.98433081601,1.76451398021,1.30058998368,-1.63939787998,-0.36542514117,-0.287133140192,0.201889222158,-0.0758819609198,-0.357690268063,0.0525519512742,-0.280203608153,-0.562545099209,0.119036743321,0.0339007122228,0.74100582402,0.32297705924,0.932621292509,0.651216891725,1.05810883748,0.326752450806,0.43800376318,0.444752956558,-0.462408473369,-0.275380563175,-0.129358145747,-0.0236512095197,0.121721165299],[-35652.7614712,990.183613961,-493.963401713,-1582.96134563,1944.299712,1733.94571927,195.951191183,-1068.7456939,103.848932325,-892.090700004,-540.230924999,484.512201502,-919.071357953,-699.034640693,-415.727492824,33.5970111923,-313.547394408,559.670336481,76.2850378456,-479.967876295,-160.679661028,-371.438827712,14.7157192859,-153.176242134,57.5603884949,-2.87522715646,-123.042161697,218.667134436,-31.8604788582,139.753320143,-117.985798651,105.793415812,-62.556427618,58.9288904453,-131.000103598,-5.62234181469,8.40500491088,24.1716218753,-26.5625469824,20.7258831245,35.449931205,-56.3773479995,11.0365072606,-63.2479132189,38.2903554033,-64.3721445644,-75.3552484331,-32.4024983597,5.59777640102,2.63681583123,3.48909911374,2.34363611442,-4.8179272269,2.9619524686,-5.5094858118,11.1146301856,-16.3219038053,7.68105127492,-3.80520638444,-20.7908578723,-6.40347352789,13.6449933266,21.1859574883,2.48017918946,3.85610187333,-3.93113334383,-3.38858908562,-0.94638118,0.716546910794,-1.5376383613,0.239258422857,0.199457849149,0.877209675814,6.74313129487,-1.65912246459,3.82939626687,5.20683204454,6.68540103455,1.25352057678,-5.35626934279,1.17317988919,-0.266590955616,0.0548710259615,-0.70826782712,-0.812518732394,-2.1065188272,0.689265879482,-1.54473059182,0.243394238365,1.00262436628,3.14446477885,1.28077791679,1.52441427288,1.89436447618,1.7287141975,1.25435685399,-1.70687691983,-0.370293908905,-0.295469624551,0.207391211984,-0.0494246931757,-0.349534610909,0.0382966436856,-0.275393478993,-0.579608134999,0.100423566856,0.034844257257,0.730491860917,0.330793044414,0.943344223181,0.639109941497,1.0418394874,0.288982858501,0.426256242798,0.431910494853,-0.48656622658,-0.262797085478,-0.132872021605,-0.0175308889195,0.119925869046],[-35720.7797039,979.090439206,-500.176970254,-1531.57404199,2023.87598675,1734.31466627,151.385559256,-1037.66324498,102.267780066,-871.864440239,-572.258670496,496.00704271,-871.265513762,-688.072270429,-442.354549392,32.720515789,-323.22390428,586.372936708,76.2694187708,-473.934243725,-152.266308862,-388.486139085,13.3461626641,-142.367964479,55.1546307359,-8.69788521989,-119.992867244,226.030592998,-32.6205018851,143.094879778,-118.273431703,110.158805089,-56.2071741606,54.0205380429,-133.916595251,-5.80023028693,6.82668446688,23.6271964988,-26.2049065223,19.6498664006,38.1706566479,-54.9969302491,12.9640064002,-60.2038198228,36.9121059223,-65.7186337022,-75.0319620686,-31.9918431062,6.22917078632,2.1182357225,3.06101049742,2.17789793137,-4.90564334507,3.32646881351,-4.99991037486,11.17752952,-15.5781127708,7.72449364871,-4.08217643764,-20.6316345669,-6.74217915072,13.4770798388,20.5844349987,2.6703932598,3.8433403243,-3.99225271555,-3.6458439109,-1.04311152069,0.688983929335,-1.62463170565,0.266744173933,0.429508411884,1.02043805261,6.72847817291,-1.64223562627,3.58902594752,5.05356607014,6.54051840129,1.17957311071,-5.43416177343,1.22743582089,-0.199514662781,0.0542864536422,-0.783661429415,-0.828908401916,-2.14934370511,0.657076215623,-1.52766867617,0.254760623122,1.05095517955,3.18387014757,1.23637191399,1.47405746144,1.80111194763,1.68611791936,1.21099680835,-1.76572167423,-0.374319577473,-0.303594939598,0.212635342589,-0.0223057887184,-0.341555983778,0.0241453235224,-0.27081803391,-0.5963201967,0.0819401328386,0.0349276408964,0.718175464738,0.338074352864,0.952035078339,0.627378848491,1.02458062734,0.251595734288,0.414124887177,0.419393826089,-0.508121282218,-0.249970495317,-0.136025019523,-0.0116193915089,0.117908605404],[-35776.7940543,954.373746471,-490.835742779,-1481.23269181,2098.64049455,1741.98364775,111.705491996,-1006.8314218,97.9994653193,-852.572425285,-604.847170505,510.552497952,-824.164211553,-675.760594835,-463.840679439,31.1323201007,-331.452824548,611.39747992,76.0969558021,-467.514803978,-142.745379739,-404.124939255,10.9618632201,-132.104422945,52.8483068441,-14.3063128234,-117.067550272,232.938199033,-33.0067999822,146.191605589,-118.703839088,113.627707654,-50.1796254036,48.7512651704,-136.131072996,-5.96783762643,5.22068809126,23.1137970642,-26.0421979848,18.6348797435,40.7107649444,-53.8062277971,14.7263171095,-57.1094530623,35.5401535547,-66.8316136082,-74.5587324674,-31.5861689509,6.84788787052,1.55900852331,2.658716424,1.96761884037,-5.00164495354,3.63600229486,-4.52157511905,11.2443019136,-14.8231894791,7.80092847296,-4.32127599626,-20.4398913627,-7.05152201247,13.2735999744,19.9398227881,2.86102638823,3.81529925737,-4.04550965426,-3.90255730927,-1.13985139395,0.646290421086,-1.71299668615,0.303383812713,0.65455236384,1.16854284572,6.71055023312,-1.61571813968,3.34929076817,4.88772580618,6.37126473466,1.10975060996,-5.49661807073,1.28172701236,-0.133924838284,0.0524241032497,-0.856623413573,-0.845880002753,-2.19289008507,0.625391638407,-1.50935539503,0.261689465545,1.10006828118,3.2178775328,1.19314865163,1.4229707005,1.70569355902,1.63657067471,1.1713783398,-1.8161145046,-0.37776725831,-0.310990348322,0.217677108555,0.00541274027657,-0.33404661961,0.0102782699882,-0.266777212388,-0.612707574575,0.0635703194891,0.0340585884398,0.704086492907,0.344520914855,0.9588787914,0.615974427331,1.00637438572,0.214928002059,0.401609529034,0.407628598888,-0.527213847956,-0.237152007019,-0.138672230602,-0.00590864883122,0.115620620855],[-35817.296334,919.540195019,-463.497106692,-1432.94824851,2170.47180836,1757.63315063,76.3586334026,-979.899958932,90.921169281,-833.741020685,-637.713895842,528.259726349,-779.378013837,-661.555224132,-480.154897242,28.874875182,-338.051055707,634.261038637,75.9095810137,-460.754944558,-132.013409844,-418.169853748,7.63066491024,-122.371107309,50.6457361529,-19.7096944843,-114.370652311,239.291250961,-32.8974632595,149.062616708,-119.274854514,116.189677048,-44.5218775161,43.1283420693,-137.784121499,-6.13849565775,3.57710958276,22.6314021525,-26.094547797,17.7348074725,43.0697920574,-52.80749393,16.320662106,-53.9925300282,34.1858643665,-67.7609491041,-73.9490549349,-31.1863981285,7.44675281315,0.960235913639,2.29587600069,1.71311053695,-5.09906559632,3.89386054489,-4.07421407576,11.3189086472,-14.0622809926,7.90572999381,-4.53655511021,-20.2245455689,-7.33346474508,13.0380883116,19.2524756505,3.05208780082,3.77276090079,-4.08651830751,-4.15519884367,-1.23761863211,0.589336887843,-1.80195464982,0.351194705768,0.871115030846,1.31876346445,6.6855397888,-1.5814962528,3.10916227773,4.71239455198,6.17653751065,1.04587037099,-5.544447774,1.33632959639,-0.0698896369007,0.0495777438565,-0.926004963889,-0.864416788044,-2.23662977351,0.593986503498,-1.48928784398,0.263567016092,1.14877020118,3.24583827583,1.15095903103,1.370627184,1.60919647941,1.57963654711,1.13624832775,-1.85835780402,-0.380752039825,-0.317269856281,0.222573306137,0.0336148380722,-0.327236628118,-0.00313077229525,-0.263439259528,-0.628723780611,0.045294041525,0.0322205583825,0.688226937727,0.349889668426,0.963891629163,0.60478716993,0.987096231216,0.17926635796,0.388555857084,0.396967970705,-0.544073981017,-0.224485183148,-0.140712443426,-0.000432340402557,0.112996875002],[-35840.1297606,873.789629776,-420.981824333,-1387.47528783,2239.54197421,1780.63863322,42.317256649,-960.855063616,81.3321021991,-815.185140271,-670.298169333,548.546106252,-738.318867164,-645.228226864,-491.538391546,26.1581149418,-342.875230684,654.679449156,75.7642586353,-453.718599106,-120.163299107,-430.609342447,3.48907835532,-113.173021798,48.5791197256,-24.8772077458,-111.986733921,245.00069693,-32.2090704083,151.694000062,-120.031223632,117.865344373,-39.3028479083,37.1698254992,-139.045545416,-6.32496833685,1.90477670079,22.1749469486,-26.3723898077,16.9913359798,45.2427289565,-52.0032839953,17.7346235957,-50.890039023,32.8545674962,-68.5583100115,-73.2164955486,-30.797614965,8.0161447008,0.327856442285,1.98340797985,1.41806605386,-5.19177117225,4.10209581435,-3.65528097668,11.3998382221,-13.3013944529,8.03171140323,-4.74127314052,-19.992066155,-7.5943699899,12.7732123539,18.5239063347,3.24232099424,3.71711241312,-4.11145834621,-4.39929488761,-1.33682292198,0.519386371388,-1.88954479105,0.410940324964,1.07640411398,1.4679627714,6.65011594519,-1.54042599343,2.86705245459,4.53072335577,5.9559512137,0.990148214897,-5.57806598016,1.39123618495,-0.00765973546763,0.0461234299345,-0.99044257458,-0.885107034345,-2.27974256461,0.562788165506,-1.46701418416,0.26011619594,1.19585688537,3.26717212481,1.1098508829,1.31641914579,1.51271825551,1.51484712991,1.10618938348,-1.89270663895,-0.383251790488,-0.322252167237,0.227346830228,0.0620563991522,-0.321293059417,-0.0158766314233,-0.260894025117,-0.644187628991,0.0270520666172,0.0294701639518,0.670668326028,0.353980274966,0.967047597909,0.593656392523,0.96662627,0.144866263358,0.374759832193,0.387680876711,-0.55891980365,-0.211983297239,-0.14210712799,0.0047278832297,0.109954557316],[-35844.6665469,816.967958538,-372.843967401,-1346.34745157,2305.32826853,1808.83911524,5.29804535337,-953.88320378,69.5207148743,-797.129128522,-701.668104541,570.432671073,-702.130281961,-626.894682528,-498.163354772,23.2637878461,-345.932701848,672.604061988,75.7190798117,-446.422366193,-107.414247799,-441.49301941,-1.16661701015,-104.518112978,46.6951846337,-29.7789277995,-109.964913717,249.993375452,-30.8907099747,154.065546823,-121.040234708,118.732460025,-34.5927255622,30.9119832596,-140.106423704,-6.53439903048,0.222305694816,21.7353674113,-26.8824437826,16.4338275486,47.2236393772,-51.3923642095,18.9546573858,-47.843902257,31.5494319231,-69.2755967009,-72.3769397398,-30.4330302274,8.54633840952,-0.328644025906,1.7285124769,1.08571680277,-5.27500095456,4.26154099668,-3.25959652295,11.4815139293,-12.5461378169,8.17026271787,-4.94574172889,-19.7463338134,-7.84492222455,12.4810503996,17.7578999683,3.42995925689,3.65037718421,-4.11731136753,-4.63054334591,-1.4372229072,0.437266957516,-1.97265068231,0.482239363175,1.26864389414,1.61326365623,6.60233743123,-1.49207596916,2.62102805101,4.34590590872,5.71009625892,0.945338013002,-5.59728984389,1.44625521874,0.052522417133,0.0424341616078,-1.04855083562,-0.908090085521,-2.32141540198,0.53187255914,-1.44218687317,0.251514215518,1.24033713335,3.28155265112,1.07021842388,1.25984351921,1.41750811539,1.44181515281,1.08174286188,-1.91929298552,-0.385033136098,-0.326095547471,0.231983153608,0.0904413584529,-0.316312090338,-0.0277213051946,-0.259141326656,-0.658866885864,0.00874466729447,0.0258990966904,0.651552600334,0.356692997133,0.968314661541,0.582433597907,0.944927757809,0.112017361253,0.359987960737,0.379950116494,-0.571929960278,-0.199517302265,-0.142910749556,0.0094259094088,0.106414346275],[-35832.158468,752.011666134,-330.118866388,-1311.14183281,2366.94735014,1839.73489272,-37.6519474945,-961.209626309,55.7540797765,-780.307246818,-730.41556802,593.105226982,-671.180174523,-606.683017774,-500.14806864,20.4729089529,-347.438825829,688.292841898,75.8462213832,-438.69942441,-93.9797332649,-450.812606965,-5.92688126446,-96.4261840987,45.0313968194,-34.4194795587,-108.264200205,254.190575513,-28.8962254722,156.169027425,-122.334213998,118.928756291,-30.4487057654,24.3890713939,-141.121602056,-6.76881241182,-1.44830239268,21.3092310954,-27.6325617273,16.0842545043,49.0077264999,-50.955137276,19.9814210745,-44.8893883817,30.2701075031,-69.9481882715,-71.4411416225,-30.1102900262,9.02974909368,-0.996855381375,1.53294407802,0.716832426969,-5.34355170338,4.37194847241,-2.87743683372,11.5584003194,-11.7979354739,8.31258644048,-5.15416692149,-19.4874118475,-8.09829506773,12.1649070005,16.9589018657,3.61335290805,3.57513292942,-4.10296716218,-4.84581473154,-1.53748600129,0.342884299402,-2.04715750559,0.563766447867,1.44775039192,1.75310938907,6.54216156382,-1.43480496598,2.36893808464,4.16186724472,5.44030177919,0.913948993588,-5.60170952078,1.50107278976,0.110530278536,0.038638370151,-1.09918749571,-0.933079872586,-2.36108854322,0.501566419777,-1.41469699224,0.238539196756,1.28179356302,3.28918355962,1.03278269662,1.20064401717,1.3251704306,1.36048578211,1.06325369547,-1.93812951155,-0.385831068484,-0.329114073858,0.236464179151,0.118476994964,-0.312305013574,-0.0384062446327,-0.258107657583,-0.672585369591,-0.00969298028748,0.0215802080441,0.631127806641,0.358089985183,0.967772584457,0.571063460258,0.922126695208,0.08110800464,0.344069495215,0.37387358448,-0.583190494291,-0.186895102182,-0.143224233984,0.0135121710694,0.102348475553],[-35806.4588309,679.132960652,-290.42678973,-1280.20370639,2422.73642359,1871.55930612,-83.8809324654,-981.657618266,40.7923704303,-765.710505941,-755.795777188,616.38466823,-644.938180443,-584.388794581,-498.971170713,17.905294597,-347.707603027,702.066257538,75.9595621355,-430.306867064,-80.0455816417,-458.708662407,-10.6885243394,-89.0936228655,43.5708148604,-38.8252404733,-106.72606536,257.452647544,-26.2088973225,157.976659651,-123.856026748,118.564117284,-26.9557965027,17.5854519678,-142.102023282,-7.02313029152,-3.08299195672,20.918171865,-28.6205083911,15.954574165,50.5829903468,-50.6401137555,20.8356550226,-42.0557519131,29.001550853,-70.5764361157,-70.3865153372,-29.8366669098,9.46432677763,-1.66263518151,1.39250626367,0.317493038144,-5.39172426165,4.43215904948,-2.49837548693,11.6304896906,-11.0542118618,8.44949932607,-5.36906868971,-19.2072012326,-8.3663969213,11.8331931412,16.1237649771,3.79074720195,3.49434301898,-4.07098995354,-5.04288629651,-1.63525372424,0.236195032884,-2.1103953981,0.653091488763,1.61497155305,1.88727626473,6.46911168863,-1.36725575354,2.10822013255,3.98405087255,5.14652421051,0.895606456884,-5.59190365781,1.55496669957,0.166246547484,0.034544760334,-1.14194445658,-0.959460906721,-2.39830831396,0.472326069889,-1.38518389775,0.22226534715,1.32030309311,3.29057696393,0.997814343355,1.13844336488,1.23750526522,1.27119778383,1.05022829409,-1.94940084648,-0.385741198799,-0.331030972893,0.240750209065,0.145848684133,-0.309084069712,-0.047742129083,-0.257666117345,-0.685215657363,-0.0281560434545,0.0165406757375,0.609711486258,0.358322229377,0.965702873895,0.559524985317,0.898421857228,0.0525145993454,0.327039397492,0.369479265585,-0.592693928625,-0.174005756461,-0.142996296696,0.0170175948327,0.0978743935474],[-35772.6035277,601.946494374,-249.330293904,-1252.78410499,2471.87616253,1903.36107992,-129.912095362,-1011.86144609,25.0766762178,-754.317427655,-777.034832419,640.403930674,-621.996450055,-559.817792908,-495.781250336,15.5373779788,-347.131031179,714.34082945,75.8952178591,-420.881777403,-65.8197266387,-465.192456474,-15.3820646559,-82.726605001,42.2771319669,-43.058120012,-105.178505883,259.670228129,-22.8315160598,159.447148603,-125.491769169,117.746890126,-24.1820722172,10.4767222933,-143.018536943,-7.29223608068,-4.66455669048,20.5773472639,-29.8400373322,16.0429083864,51.9381531957,-50.3842114223,21.5359022254,-39.3591724491,27.7196093178,-71.1443697142,-69.1888164675,-29.6126223549,9.85018891506,-2.31463236834,1.29903317848,-0.106588458022,-5.41667707182,4.44132629263,-2.11092289492,11.6961775974,-10.3084226711,8.57024210516,-5.58792082085,-18.8971881479,-8.65897152833,11.4943173514,15.2489610634,3.96046187678,3.41039364443,-4.02524159235,-5.22077927377,-1.7283142069,0.11765769093,-2.16017814172,0.747436075522,1.77309116689,2.01569660309,6.38409863613,-1.28857250547,1.83711731324,3.81751373685,4.82910573253,0.889310236731,-5.5684384422,1.60727500174,0.219475317561,0.0299917618039,-1.17683449885,-0.986576711576,-2.43257480453,0.444629667717,-1.35429435023,0.204038284425,1.35612741389,3.28656644831,0.965318871297,1.07311138268,1.15606594514,1.17448963869,1.04184569637,-1.95328872581,-0.384968516048,-0.331584211664,0.24487601184,0.172275641678,-0.306396242649,-0.0556103803346,-0.2576590816,-0.696643154307,-0.0465735047155,0.010870837027,0.587654351214,0.357574440747,0.96243964674,0.547773707169,0.874068724999,0.0265164610103,0.308983653841,0.366676721849,-0.600378374297,-0.160765182785,-0.142172885012,0.0199819930749,0.0931487635603],[-35734.6750816,528.176151752,-200.375293583,-1229.40109732,2514.83518446,1935.44215536,-172.946119254,-1047.5260786,8.66411646298,-746.854880232,-793.318065615,665.345443968,-600.480116365,-532.94196029,-490.909142951,13.247256549,-346.077037367,725.539713287,75.5667480436,-409.980483025,-51.5412390514,-470.071545639,-19.9502743628,-77.4474905591,41.1026232856,-47.1908846301,-103.482101276,260.786659862,-18.7696018777,160.523469583,-127.089956781,116.563938216,-22.1410444182,3.0379884781,-143.833627817,-7.57686920947,-6.18213944327,20.2883048024,-31.280219575,16.3380851287,53.0635601569,-50.1215897719,22.088594801,-36.7955360221,26.3946719283,-71.6299721611,-67.8312825166,-29.4350512682,10.1877799772,-2.94596410153,1.2424036416,-0.550260979483,-5.41875268133,4.39921768345,-1.70305787257,11.750669592,-9.54933851608,8.66255067515,-5.80354520203,-18.5503872911,-8.9831771452,11.1544749243,14.3321743749,4.12090967577,3.32440669788,-3.96981854242,-5.37939003625,-1.81528133509,-0.0115225827228,-2.19478643224,0.844188209131,1.92619507444,2.13800256461,6.28960075024,-1.19852244044,1.55498743018,3.6658977608,4.48899468125,0.894211149377,-5.53162946004,1.6575060809,0.269817648091,0.0249551171934,-1.20412645082,-1.01398435905,-2.46324217892,0.418814771353,-1.32235410174,0.18528535501,1.38954406094,3.27830381307,0.935044145111,1.004848606,1.08194026208,1.07106373234,1.03726491682,-1.94989334325,-0.383692111112,-0.330693708952,0.248970424845,0.197519997321,-0.303983243888,-0.0619720821271,-0.257937824168,-0.70673813365,-0.0649771408307,0.00477530444934,0.565274118231,0.356030266257,0.958351047282,0.535702776494,0.849367508473,0.00324290814243,0.290009738914,0.36529164095,-0.606136320701,-0.147110604579,-0.14071637811,0.0224134960121,0.0883315556032],[-35693.553627,463.902222604,-141.706659516,-1210.73041103,2552.72417913,1967.13713613,-211.032166863,-1086.1723382,-8.32825740474,-743.583045923,-804.309623155,691.28250797,-579.191067963,-503.828531626,-484.514059596,10.9324299134,-344.750749041,735.984141439,74.9411395969,-397.369291369,-37.4378404616,-473.24660837,-24.4197353995,-73.3818790723,40.0057958296,-51.2628255587,-101.530317794,260.805180482,-14.0771865452,161.143892564,-128.555127328,115.056918945,-20.8380819524,-4.75198712594,-144.517278466,-7.88166085892,-7.62265006346,20.046576264,-32.9187641044,16.8209334241,53.9500606384,-49.8064155926,22.4865046907,-34.3628069424,24.9953305724,-72.0209757481,-66.3046113981,-29.3024645583,10.4766189201,-3.55312617784,1.21348112665,-1.00685628325,-5.39951402209,4.3065319807,-1.26715753051,11.7876008353,-8.76921048217,8.71377928996,-6.01109119118,-18.160516709,-9.34572585996,10.8177970842,13.3711808182,4.27013322294,3.23635066195,-3.90831543419,-5.51885330465,-1.89478598526,-0.149310371907,-2.21350602511,0.941358796809,2.07749745318,2.25370198977,6.1874512418,-1.09705369834,1.26115362289,3.53125085296,4.12694155516,0.909373277474,-5.48196630831,1.70514488583,0.316655293958,0.0196090421237,-1.22426397515,-1.04125210991,-2.48946888894,0.395170840438,-1.28931003432,0.167101874525,1.42089676314,3.26659253351,0.906660517168,0.933628460881,1.01575255393,0.96146724062,1.03566342416,-1.93944845464,-0.382013478734,-0.32844595378,0.253194041787,0.221355423485,-0.30159531609,-0.06686656475,-0.258327337218,-0.715337881017,-0.0833903721645,-0.00141875225168,0.542804840257,0.353902069337,0.953705008648,0.523221183859,0.824488688081,-0.0172844860579,0.270125995591,0.365102848807,-0.60990785982,-0.13301004358,-0.138597384879,0.0243092276004,0.0835666775766],[-35647.5678254,409.720699479,-75.0251191219,-1197.15271493,2586.10242507,1997.44069863,-243.64363817,-1125.99854322,-25.5985794014,-744.372866051,-809.813250748,718.023851844,-557.493226916,-472.490649813,-476.727182217,8.6029122379,-343.120639569,745.942324736,74.0435037518,-383.015680153,-23.6666393144,-474.729186025,-28.9273207871,-70.6699702444,38.9746563021,-55.2486602033,-99.2335929876,259.791697342,-8.84480226761,161.255971722,-129.8625757,113.204935895,-20.2869407096,-12.9229307024,-145.038775433,-8.2111162886,-8.96529231946,19.845162838,-34.7154182802,17.4680196904,54.5880716064,-49.4169684665,22.7075670006,-32.0667100347,23.4888236531,-72.3123072546,-64.605767159,-29.2148689676,10.714538088,-4.13431614457,1.20370277647,-1.46704199301,-5.36006941903,4.16483754871,-0.80063135425,11.7999665147,-7.96453702427,8.71079789229,-6.20769369553,-17.7218404129,-9.75175441247,10.4863060153,12.3637503213,4.40537551819,3.14512937615,-3.84377929266,-5.63928058944,-1.96499324457,-0.292928931616,-2.21624623081,1.03766290123,2.2290940542,2.36227680958,6.07887661821,-0.983914242039,0.955186531727,3.41418077244,3.74312160534,0.93357189446,-5.42046235617,1.74947700422,0.359113130898,0.0142900685949,-1.2378345979,-1.06780883298,-2.51022602626,0.374096860927,-1.25469753361,0.150296882245,1.45067526895,3.25185866888,0.879959034974,0.859235197694,0.957717932077,0.846063479006,1.03620897508,-1.92234094299,-0.379935343563,-0.325031714528,0.257690598153,0.243529451257,-0.298988567294,-0.0704099939702,-0.258618807713,-0.722232354245,-0.101733175619,-0.0072708573304,0.520421267533,0.351475312807,0.94866347218,0.510313128258,0.799485729082,-0.0351254921831,0.249234845502,0.36583918424,-0.611687514938,-0.118486378132,-0.135776911528,0.0256656247576,0.0789676819985],[-35593.8733331,363.75511845,-1.16658679977,-1188.7304688,2615.19367298,2026.46599958,-270.895389707,-1164.61183592,-42.9398922834,-748.775057697,-809.515874339,745.343427034,-534.857719905,-438.781950941,-467.48833357,6.33411613783,-340.996782852,755.663428613,73.0021988391,-366.954948717,-10.2387201966,-474.523021321,-33.653829916,-69.4356009793,38.0179929175,-59.0823149854,-96.5177253447,257.861841977,-3.16214713416,160.831884073,-131.026306546,110.941073863,-20.4896593742,-21.5092366278,-145.349914777,-8.56800850793,-10.1881847481,19.6767650224,-36.6197568768,18.2523491653,54.9712990505,-48.9486727322,22.7207949911,-29.9113322971,21.8463092117,-72.4977292867,-62.7329594477,-29.1699353199,10.8991021221,-4.68916950408,1.20464517527,-1.92150356422,-5.30069247516,3.97619608455,-0.30464292849,11.7813939383,-7.13321521512,8.64156596769,-6.38891964201,-17.2279207368,-10.2023734846,10.1602052175,11.3084216306,4.52345195753,3.04874547951,-3.77866279926,-5.74135341678,-2.02378991174,-0.439390640518,-2.20322304857,1.13245842161,2.38243351718,2.46367767498,5.96536668968,-0.858287603346,0.637641561263,3.31405275723,3.33743546277,0.965371108005,-5.34834553302,1.78967683602,0.396202201617,0.00939431823286,-1.24558354507,-1.0929225002,-2.52457574973,0.356128027992,-1.21768863586,0.135462049844,1.47958778659,3.23438256163,0.854945632702,0.781557348381,0.907724065288,0.725270728488,1.0381352537,-1.89888707659,-0.377370162192,-0.320688275248,0.262577239722,0.263810962541,-0.295945603823,-0.0727781076788,-0.258571741973,-0.727223223008,-0.119811688748,-0.0122972146699,0.498249523583,0.349078664155,0.943314773341,0.497061852354,0.774370518723,-0.0503983160301,0.227224016704,0.367198531785,-0.611435339139,-0.103624572869,-0.132179179203,0.0264678448657,0.0746411485019],[-35529.2908281,322.278421413,77.0412021452,-1185.17283124,2639.9323326,2054.48381492,-292.915402741,-1200.01723042,-60.2703205795,-756.060252324,-803.30295663,773.204159591,-511.09939535,-402.340296717,-456.818022554,4.24717284795,-338.089628337,765.356749828,72.0331210331,-349.384683143,2.98582020704,-472.732960205,-38.8376559765,-69.7781355894,37.1590601898,-62.6752517514,-93.3253441941,255.166387721,2.86433090812,159.871513259,-132.119520015,108.163418806,-21.4485604362,-30.5294271258,-145.393816223,-8.95329934197,-11.2719403786,19.5375784044,-38.5774966737,19.1409355873,55.1004553103,-48.4188546562,22.4898083289,-27.9053098783,20.0480783743,-72.5729507851,-60.6854729006,-29.1641357856,11.0286452367,-5.21846991889,1.20911219574,-2.36184609168,-5.220369827,3.74297147508,0.214490877524,11.7268448996,-6.27757630177,8.496718354,-6.55059575171,-16.6716381549,-10.6967006429,9.83788310868,10.2042537834,4.62104086603,2.94470793768,-3.71461826745,-5.82656260779,-2.06873625285,-0.585748523615,-2.17546682971,1.22577561853,2.53754422477,2.55846502017,5.84787954446,-0.718698876915,0.309365619263,3.22925654914,2.90964523162,1.00321458714,-5.26700923883,1.82489262945,0.42697104687,0.00534507373742,-1.24839591435,-1.11566131742,-2.53183254257,0.341867744517,-1.17717934245,0.122798735505,1.50854281113,3.21411297648,0.8318630658,0.700422072161,0.865385480607,0.599532464001,1.04076451559,-1.86933754976,-0.374143715648,-0.315671721777,0.267934589493,0.282020079022,-0.292301143226,-0.0741969494722,-0.25790429141,-0.73016001939,-0.137315784138,-0.0160197240099,0.476357144179,0.347063841306,0.937623319372,0.483669289178,0.749054081605,-0.063262635165,0.203943192819,0.368890761386,-0.609078635778,-0.0885411909749,-0.127698656456,0.0266980522032,0.0706701837401],[-35451.7049208,274.972223409,155.069954595,-1185.88982173,2658.99456812,2082.00062477,-310.656263307,-1230.77087578,-77.359891351,-765.423793364,-791.218051039,801.367356116,-486.336590968,-362.920238273,-444.936158111,2.55014654124,-334.029442019,775.196343274,71.3213771197,-330.645607053,16.1514032082,-469.614431916,-44.8093715499,-71.7952267054,36.4421887161,-65.9104259725,-89.6147181511,251.867091792,9.11109340094,158.361687173,-133.266189268,104.721230519,-23.1755261015,-39.9776074068,-145.120452095,-9.36594965377,-12.1940227589,19.425765428,-40.5310572972,20.099226478,54.9765127582,-47.8629672051,21.9660948945,-26.0679022595,18.0808637472,-72.5432531069,-58.4668033312,-29.1942769356,11.101424343,-5.72258065826,1.21148910191,-2.77884511769,-5.11655043621,3.46744371809,0.745824953923,11.6298057466,-5.40575445106,8.26809174566,-6.69113701942,-16.0466346173,-11.233443688,9.51666170795,9.05072505639,4.69448778632,2.83049356099,-3.65266639696,-5.89643750273,-2.0971282412,-0.728955766368,-2.13468458987,1.31763904102,2.69289848938,2.64694481212,5.72626322464,-0.563834617909,-0.0291193500751,3.15745729707,2.45937143704,1.04544523501,-5.17815605333,1.85422883361,0.450471275748,0.00256589889298,-1.24715272319,-1.13500295076,-2.531428341,0.33198823183,-1.13200491085,0.112185505042,1.53834282815,3.19062104002,0.81100468747,0.615454795748,0.830090919389,0.469229387697,1.04353938717,-1.83404250158,-0.370015513652,-0.310247342335,0.273810248442,0.297979017602,-0.287944808929,-0.0749234453388,-0.256330013821,-0.730910826128,-0.153838514773,-0.0179803485886,0.454792922863,0.345741901215,0.931452785843,0.470397599262,0.723320516512,-0.0739411814102,0.179169460554,0.370665552939,-0.60456486174,-0.0733821615688,-0.122214067949,0.0263389213143,0.0671104494003],[-35359.1537781,212.716444287,227.038995279,-1190.79345929,2671.65717771,2109.12248232,-325.115569272,-1257.01542368,-94.0740870589,-776.046089449,-773.489904354,829.739178853,-461.187975531,-320.362007336,-432.244876757,1.41291248909,-328.4889869,785.28352069,71.0996128222,-311.216053245,29.3914796501,-465.564267032,-51.8808038374,-75.6005808422,35.9115696936,-68.6909085464,-85.3624287221,248.129217193,15.4398307798,156.29446099,-134.632183415,100.470044969,-25.7051046801,-49.8135017304,-144.511534464,-9.80094201843,-12.9397766224,19.3409432758,-42.42639562,21.0959723106,54.605469637,-47.3331906577,21.1009370392,-24.4329459401,15.9435813391,-72.430266989,-56.0827555627,-29.25678116,11.1167308035,-6.20272740607,1.2085067058,-3.16517551214,-4.98644304951,3.15310094273,1.27415538142,11.4841384656,-4.53167828907,7.95144875711,-6.81438731191,-15.3473662,-11.8122070545,9.19339707552,7.84780016771,4.74065454666,2.70402750067,-3.59332151019,-5.95298190508,-2.10624803866,-0.866089138049,-2.08293963338,1.40810310656,2.84533139347,2.72973874531,5.59877248079,-0.392621827893,-0.37778305597,3.09643695056,1.98618582828,1.09076913773,-5.08398009664,1.87692928558,0.465914892079,0.00145059912947,-1.24279124522,-1.14995345291,-2.52300909481,0.327172551608,-1.08115141838,0.103213486925,1.56972451515,3.16310287475,0.79280464739,0.525995859199,0.801292948339,0.33464078832,1.04615507616,-1.79356923919,-0.364722829185,-0.304742312808,0.280235530755,0.311553217745,-0.282820593668,-0.0752116807453,-0.253594146649,-0.729427647288,-0.168928041348,-0.0177888191046,0.433605453688,0.345368617582,0.924609167199,0.457590936227,0.696825939549,-0.0826305673629,0.152606044546,0.372401818623,-0.597916021914,-0.0583181541611,-0.115649014306,0.0253702787913,0.0640006043078],[-35250.2586405,130.119045283,288.574579225,-1199.97456985,2677.86034333,2135.65477653,-336.617228762,-1280.57862875,-110.248803972,-787.288630253,-750.588523082,858.371597445,-436.807546538,-274.707569572,-419.371997084,1.00612175485,-321.272152841,795.586135442,71.5690235575,-291.688147749,42.7516011469,-461.072450812,-60.2976215219,-81.239133413,35.6110870885,-70.9509842583,-80.5761558474,244.075723472,21.7153112942,153.654387096,-136.398242877,95.2953587004,-29.0628452211,-59.948694143,-143.587644635,-10.2511073304,-13.4997518356,19.2850951688,-44.2210182742,22.109435382,53.9954914364,-46.8861301653,19.8493996882,-23.0417570472,13.6530245807,-72.2713930931,-53.545957672,-29.3462152862,11.0737950701,-6.65818950039,1.20045309583,-3.51515710005,-4.82631921008,2.80461824097,1.78269474241,11.2840303692,-3.67377245697,7.54658711343,-6.92880076649,-14.5715216812,-12.433072802,8.8650395407,6.59739411617,4.75679980543,2.56446512052,-3.5362742792,-5.99769586426,-2.09373304091,-0.994220804792,-2.02226016614,1.4967386415,2.99019720241,2.80720964813,5.46270860302,-0.204982407716,-0.736505812053,3.0443556541,1.49044182598,1.13830741639,-4.98739464983,1.89237220142,0.472694820563,0.00234105400865,-1.23598792951,-1.15974006789,-2.50635995698,0.328004049238,-1.02393587185,0.095275639392,1.60301771057,3.13061183699,0.777625588207,0.431323643221,0.77851000497,0.19624234539,1.04854661746,-1.74877441553,-0.358010435322,-0.299553430359,0.287224771414,0.322577718973,-0.276957184202,-0.0752618062602,-0.249525944853,-0.725717471611,-0.182143483222,-0.0151419469697,0.412874832448,0.346062754688,0.91690702361,0.445607340044,0.669205627719,-0.0895324732849,0.123968716518,0.374108256202,-0.589243990991,-0.0435687466716,-0.107990976929,0.0237647960314,0.0613672699089],[-35124.7866892,29.2951645051,338.203857722,-1213.2987289,2678.33118544,2161.04384688,-344.967456255,-1304.98191517,-125.660791391,-798.8292059,-723.432512811,887.283525845,-414.8808007,-226.425693945,-406.913864383,1.50243147727,-312.385974102,805.901838112,72.8160425279,-272.754984577,56.1064333631,-456.596569878,-70.2054921395,-88.6000381251,35.5745240776,-72.6581863964,-75.2985262392,239.765119228,27.8184159313,150.399793167,-138.725676181,89.131478062,-33.2330317301,-70.2534491802,-142.401807211,-10.7087081704,-13.8678275654,19.265050256,-45.885529574,23.1280863156,53.1563250472,-46.5731683678,18.1766165325,-21.9320761937,11.2423075933,-72.1151208376,-50.8788707948,-29.4537750685,10.972467532,-7.08464794236,1.19148526391,-3.82360204293,-4.63133959537,2.42808271197,2.25457909064,11.0244275641,-2.85271633181,7.05644916135,-7.04639373851,-13.7223303605,-13.0956865572,8.5277933661,5.30410641074,4.74088961203,2.4126086684,-3.48030659379,-6.03099939923,-2.05798630233,-1.11023403436,-1.95464711449,1.58226102455,3.12164932018,2.87905419712,5.31466679123,-0.00269178623181,-1.10455614075,2.99956105652,0.973973850933,1.18757405085,-4.89208304356,1.90012865001,0.470455044917,0.00548387007995,-1.22697789014,-1.16386983746,-2.48139338435,0.334794354862,-0.96011644342,0.0875409124509,1.63796889659,3.09215463526,0.765441875883,0.330860751542,0.761215207793,0.0550270884094,1.05079716836,-1.7007735213,-0.349667976841,-0.295175044515,0.294744646525,0.330852533487,-0.270483942168,-0.0751939261156,-0.244051987689,-0.71982303061,-0.193110175142,-0.00986236149124,0.392697482229,0.347763475788,0.908196515942,0.434739758135,0.640130899231,-0.0948841988975,0.0930779180538,0.375885818527,-0.578734922574,-0.0294269830961,-0.099312143099,0.02149227415,0.0592361702024],[-34982.9829368,-81.8434194623,379.4623235,-1230.55633048,2674.48781094,2185.82605278,-350.360422576,-1332.71607032,-140.193798602,-810.637578409,-693.042535062,916.195559187,-396.583451355,-176.437691873,-394.81801628,3.0976193102,-302.060895186,815.915710755,74.758611165,-255.002516638,69.1353828194,-452.274479077,-81.6693788826,-97.3333734631,35.8559829785,-73.818958465,-69.6227687445,235.186473832,33.6443155564,146.43149125,-141.667163168,81.9399381394,-38.0978139558,-80.577377727,-140.993394481,-11.1510616613,-14.0371165267,19.2825180154,-47.4046337835,24.1339833749,52.0866802323,-46.426674114,16.0484242242,-21.1126626017,8.74425654845,-71.9958400445,-48.1142307452,-29.5577115004,10.8164627031,-7.47042443426,1.18640966928,-4.08533729071,-4.40008892108,2.02665147102,2.6721183772,10.6967588843,-2.08453752225,6.48099772452,-7.17338655448,-12.8101144281,-13.7935823684,8.1763658535,3.97614926865,4.6913240393,2.25228551254,-3.423489701,-6.05184245678,-1.99892757865,-1.21161183917,-1.88339261027,1.66131483553,3.23379857699,2.94280566724,5.1526977817,0.209392300707,-1.47853384264,2.95983871486,0.440808039711,1.237883695,-4.801910641,1.89957731055,0.459478270224,0.0111398425588,-1.21522223995,-1.16206087067,-2.44805788089,0.34721532645,-0.890160292421,0.0789189489626,1.67346885113,3.04699172299,0.755308241566,0.224836027726,0.748454892203,-0.0871317061497,1.05274663056,-1.65069391148,-0.339592937056,-0.292103510669,0.302556800736,0.336175085662,-0.263551129719,-0.0749171631139,-0.237133295288,-0.71167573274,-0.201583558347,-0.00194055929531,0.373078748654,0.350175853147,0.898327083559,0.425045273236,0.609413365494,-0.0991104959102,0.0600007702389,0.377741258587,-0.566537629397,-0.0162905482778,-0.0897118020568,0.0185092670717,0.0576405142808],[-34827.0413696,-193.265057428,417.048901262,-1251.93246524,2668.29539578,2211.10784075,-353.495862903,-1364.66459693,-153.967052785,-822.598450408,-660.433154376,944.822689835,-382.450110766,-125.875625607,-382.666510063,5.90849498408,-290.582419025,825.285165232,77.3185189895,-238.92628237,81.4430531139,-448.065820327,-94.7116873543,-106.977758035,36.4928575958,-74.4706249522,-63.6659141396,230.33374141,39.0786586215,141.640763106,-145.207485343,73.7057141817,-43.4952863351,-90.7552029267,-139.372268045,-11.552682537,-14.011625865,19.3333663753,-48.7607075255,25.0969240935,50.7911163619,-46.4676256132,13.4370747666,-20.5762700968,6.18794915305,-71.9278953473,-45.2903963218,-29.6237154812,10.612120979,-7.80451155984,1.18955610015,-4.2958325476,-4.13433253888,1.60508380861,3.01677403516,10.2934248482,-1.3827470399,5.81863280202,-7.30951082251,-11.8492792873,-14.5150885756,7.80350112371,2.6235520217,4.6072898289,2.08782912656,-3.36362365718,-6.05955362177,-1.9172556421,-1.29572661922,-1.81277051382,1.73062655518,3.3209670228,2.99537993832,4.97613760634,0.424521127595,-1.85286867586,2.9222198067,-0.103809338388,1.28795797797,-4.72072896199,1.89022565569,0.440370420757,0.0195807204296,-1.20023212776,-1.15403882046,-2.40641491478,0.36454649059,-0.814652518451,0.0682653937954,1.70829505453,2.99446161075,0.745748008123,0.114124172327,0.738853955519,-0.227888025779,1.05380729087,-1.59967062111,-0.327748218929,-0.290873444334,0.31037426617,0.338425263918,-0.256296689721,-0.0743381527034,-0.228711224647,-0.701223499254,-0.207394459796,0.00854610274039,0.353967723151,0.352999226146,0.887087842021,0.416489341624,0.576954844837,-0.102779228047,0.0249556429796,0.379523849449,-0.552767739339,-0.00460783695407,-0.0793268107595,0.0147731759078,0.0565938669497],[-34660.8069035,-300.826653022,453.560380769,-1277.49840144,2660.52232508,2237.47055787,-356.294643136,-1400.781451,-166.904709409,-834.557042462,-626.685202264,972.689130252,-372.658340129,-76.0187932748,-370.177060579,10.0449258436,-278.158750823,833.625382404,80.4182502543,-224.990591768,92.5745732673,-443.961533034,-109.33673874,-117.097945085,37.5112262778,-74.6411054403,-57.553214708,225.217184868,43.9882511276,135.91890307,-149.322918865,64.4361473404,-49.2829401697,-100.594101663,-137.519562296,-11.8905577049,-13.7990072344,19.4084416602,-49.9268375208,25.9787635784,49.2822058525,-46.7130744458,10.3243034136,-20.3164488036,3.6075426481,-71.906749163,-42.4436624546,-29.608237671,10.3661194814,-8.07792782202,1.20558606616,-4.45047598452,-3.83765247814,1.1712175247,3.27057485165,9.81007064224,-0.761045311159,5.07000517979,-7.4492563913,-10.8542563688,-15.2453443963,7.40090370822,1.2570342354,4.48855786578,1.92323181855,-3.29821963155,-6.05380997763,-1.81376731813,-1.35963281659,-1.7469364817,1.78786630978,3.37770093493,3.03431385306,4.78505001194,0.63573743604,-2.22055194224,2.88360939493,-0.653997405861,1.33614654404,-4.6522116262,1.87174188972,0.413857296644,0.0311223331664,-1.18171783165,-1.13949141592,-2.35657939675,0.38597159509,-0.734089183427,0.0545944191951,1.74138304739,2.93380396492,0.735204693545,2.38797505414e-06,0.73088183769,-0.364637571213,1.05308893564,-1.54869924751,-0.314083475763,-0.292013752347,0.317920727835,0.337565677775,-0.248838781933,-0.0733993299241,-0.218699375929,-0.688474494071,-0.210409870029,0.0214613146463,0.335310086459,0.355967417274,0.87417860934,0.409036253298,0.54270019274,-0.106502367418,-0.0117317548087,0.380986762657,-0.53744284704,0.00518834439397,-0.0683114564609,0.0102686211986,0.05609884942],[-34488.5037243,-409.337716184,486.83291731,-1306.63845616,2650.48662776,2263.89754159,-361.674575005,-1441.63476775,-178.56353594,-846.189389152,-593.072866083,999.066842593,-367.421145521,-28.1838383002,-357.557722993,15.6089424882,-264.851816615,840.515940733,84.0112635689,-213.660887418,102.080437406,-440.140878686,-125.456768397,-127.419088778,38.9097225047,-74.3243051162,-51.4094270467,219.87883112,48.2323991009,129.17822353,-154.015602047,54.1950269643,-55.3828860379,-109.854473137,-135.394742469,-12.1482540403,-13.4094028459,19.4956528154,-50.8622291753,26.7409704462,47.5836885245,-47.1760115108,6.71029334129,-20.3402222425,1.05312385958,-71.9163618045,-39.5991440525,-29.461326941,10.0844511242,-8.28564590749,1.23915977438,-4.54379176682,-3.51448156652,0.736688951767,3.41852630849,9.24763417512,-0.234364421274,4.2420941009,-7.58415982672,-9.83422315777,-15.9676682865,6.96090841575,-0.112249958846,4.33559437841,1.76137706689,-3.22493143818,-6.03461209837,-1.68947523798,-1.40000275985,-1.68881128978,1.83187765983,3.39938523655,3.05865530429,4.57973565381,0.837507407733,-2.57366279676,2.84164291265,-1.20344087939,1.38073464875,-4.59949436036,1.84406361523,0.380625779495,0.0460053909265,-1.15970338057,-1.1182054519,-2.29870906726,0.410732247694,-0.648919673376,0.0374041613487,1.7718644418,2.86414825873,0.722389770602,-0.116042606049,0.723300770566,-0.494617297994,1.04965180667,-1.49846701706,-0.298441535382,-0.296051815159,0.324965918534,0.333650313778,-0.241278154603,-0.0721226952427,-0.207048459692,-0.673502860754,-0.210568765314,0.0365948059253,0.317129865992,0.358808223849,0.859262476088,0.402671406382,0.506616632048,-0.110803349364,-0.0496454404516,0.381887527461,-0.520424743398,0.0127462161447,-0.0568117189643,0.00501992398219,0.0561765253082],[-34314.832885,-524.06752538,512.197616572,-1339.43284555,2637.86125482,2288.20748298,-372.24264833,-1487.6363685,-188.805942243,-856.897269711,-561.11813568,1023.52602202,-366.743649987,16.4853917382,-345.334384616,22.5207857951,-250.691210639,845.47216522,88.2260148679,-205.399672155,109.626788189,-436.919250568,-142.878992077,-137.807747462,40.6387902571,-73.5339850323,-45.3680325653,214.411495534,51.6464150924,121.38760365,-159.315819291,43.1080288779,-61.7724003837,-118.270122448,-132.92795145,-12.313445584,-12.8713147557,19.5808802705,-51.5168727983,27.3359462327,45.7396654178,-47.8710571066,2.61567981274,-20.665208017,-1.41703089451,-71.9261368336,-36.769979545,-29.1250992047,9.77504975954,-8.42959883111,1.29559636321,-4.57296082496,-3.17141246544,0.317815733856,3.44660160912,8.61400033544,0.180782615192,3.34731887914,-7.70207781975,-8.79332857167,-16.663162586,6.47569165951,-1.47291701187,4.15036932333,1.60380801148,-3.14145290135,-6.00365873778,-1.54544620213,-1.41336991258,-1.64037711088,1.86330895498,3.38184065479,3.06936893569,4.3606539307,1.02571081498,-2.90343546265,2.79423704149,-1.74568932421,1.4197149132,-4.565189591,1.80759924155,0.34143426683,0.0644206596435,-1.13485134939,-1.08989984714,-2.23328825543,0.43815918854,-0.559406573516,0.0165077634345,1.79935652156,2.78444251509,0.706338762186,-0.232420894684,0.715030108539,-0.615088153343,1.04236794919,-1.44941903615,-0.28060859585,-0.303563386718,0.331358581129,0.326910157778,-0.233712071748,-0.0706497683488,-0.193711338652,-0.656552218635,-0.207858769707,0.0536624064897,0.299516543747,0.361332649993,0.841925373599,0.397451166858,0.468653268481,-0.116141639977,-0.0883326013039,0.381921238333,-0.501471339532,0.0177728172887,-0.0450048621736,-0.000924719465102,0.0568648551681],[-34142.2862691,-640.735076069,533.421422551,-1377.08176396,2625.27174278,2310.37477583,-389.8777524,-1536.22049118,-198.352735905,-865.42706167,-531.978382092,1046.34429572,-369.524875462,57.0380542506,-333.88415772,30.3227427403,-235.654587078,847.998622537,93.5286162592,-200.405396669,115.07918648,-434.477154308,-161.30041859,-148.129292925,42.5552634451,-72.3496030444,-39.5754782498,209.006704764,54.1075731902,112.623734489,-165.185969434,31.371910874,-68.4181073947,-125.567852551,-130.013168271,-12.3850892642,-12.2546266099,19.6442328265,-51.8259847836,27.7172118714,43.8320953786,-48.7892793209,-1.90728011816,-21.2939837992,-3.73775907225,-71.8845906783,-33.9599026994,-28.5336186073,9.44928348181,-8.52535928775,1.37949908569,-4.5405063901,-2.81751063301,-0.0601329811566,3.34805339246,7.92894720195,0.474912259497,2.40441399097,-7.78270239887,-7.73212580029,-17.3081552221,5.93677262258,-2.81239174011,3.9377450623,1.44966174782,-3.04567811791,-5.96643095094,-1.38324388696,-1.39586182252,-1.60197765551,1.88603398729,3.32360329037,3.0700142261,4.13059665072,1.1976428669,-3.19887236971,2.7393751536,-2.27370556441,1.450624986,-4.55187896863,1.76368204407,0.297210535561,0.0865599195336,-1.10916614618,-1.05437704277,-2.16146784391,0.46759589744,-0.465374024872,-0.00750946558378,1.8243883677,2.6942728714,0.686600199273,-0.346805313927,0.705111168037,-0.722988904462,1.02986644966,-1.40184379256,-0.260303086596,-0.315199035219,0.337113524361,0.317886455495,-0.226226099305,-0.06937918852,-0.178663488635,-0.63823407192,-0.202378603476,0.0723255779114,0.282682997768,0.363585525904,0.821912794601,0.393595841662,0.428979537366,-0.122907710262,-0.127151859001,0.380684199566,-0.480258711972,0.0199943843086,-0.0331265189066,-0.0074927648706,0.058207177696],[-33971.8015778,-753.124854905,565.10679464,-1420.54479603,2615.76418758,2332.48821515,-418.796283319,-1581.69129447,-208.155927605,-870.485305916,-506.741073594,1067.28982566,-373.745047139,91.9511929838,-323.303069015,38.4254255616,-219.629282949,847.468794242,100.397769936,-198.664538885,118.159520742,-432.843724454,-180.382225584,-158.267791646,44.4789049788,-70.852806662,-34.212898124,203.915257326,55.5080187422,102.969396434,-171.531969765,19.2011579428,-75.2882026713,-131.482166354,-126.525062904,-12.3663650473,-11.6386736115,19.6600369923,-51.7032988164,27.8299974091,41.956827094,-49.9076292384,-6.79498303566,-22.220268881,-5.8436766026,-71.7308292479,-31.1654654588,-27.6184737359,9.12063752436,-8.59301482008,1.49550019899,-4.44728698754,-2.4672246846,-0.364615145762,3.12109207504,7.21658841322,0.643443272147,1.43428989867,-7.8017384081,-6.64909404253,-17.8756211511,5.33471121716,-4.11645578246,3.70407698181,1.29702375031,-2.9351282391,-5.92948547753,-1.2052393847,-1.34230977825,-1.57339028032,1.90531616841,3.22519510373,3.06481931665,3.89375808473,1.3510790919,-3.44729071135,2.6748819742,-2.77978747367,1.47076444748,-4.56216273341,1.71393983979,0.248973814138,0.11273514529,-1.08524712951,-1.01144506309,-2.08445680648,0.498215887156,-0.366469299103,-0.033505257941,1.84775414784,2.59367305588,0.662768820531,-0.456251985938,0.692631851963,-0.814876495939,1.01069430122,-1.35588107722,-0.237133868893,-0.331745554531,0.342261412394,0.30725185568,-0.218873675629,-0.0688616563882,-0.161826855482,-0.619318368138,-0.19435185682,0.0922603384867,0.266899441815,0.365682553365,0.799112572518,0.391302804941,0.387947757113,-0.131481891878,-0.16528830265,0.377695818573,-0.456414231032,0.0191530130267,-0.0214931261376,-0.0145764838558,0.0602576006667],[-33803.9199988,-851.829046489,620.527703482,-1469.40941646,2612.84070333,2356.34936713,-460.297068509,-1617.5613481,-218.81409659,-871.040102319,-486.159922244,1086.96733911,-377.164183687,120.562361038,-312.750712988,46.2539650029,-202.520887893,843.430988753,109.370526714,-199.983952935,118.949365899,-431.65707552,-199.590467563,-167.872122097,46.2071449696,-69.1363955359,-29.4051768877,199.346495984,55.7956742099,92.5894749203,-178.159654902,6.88561867806,-82.2353380474,-135.770514563,-122.301628,-12.2690325706,-11.1046535502,19.6071806353,-51.086912065,27.6314588572,40.2069923637,-51.1920977764,-11.9608652716,-23.4002131357,-7.67615540004,-71.3850489911,-28.3740852217,-26.3155648939,8.80190309701,-8.65320778216,1.64465241182,-4.30047681614,-2.13619945398,-0.568938658434,2.76457862065,6.50402634519,0.68831252731,0.457241768351,-7.72861911939,-5.54034137866,-18.339408888,4.66263697395,-5.37109939957,3.45658949282,1.14400712002,-2.80910258051,-5.89971832303,-1.01461356138,-1.250281648,-1.55543646946,1.9262919841,3.08718279073,3.05803968061,3.65586260659,1.48436596358,-3.63604384399,2.60057534049,-3.25683426024,1.47842699225,-4.59842870402,1.66027319405,0.197920721771,0.142898411352,-1.06531517011,-0.961271963086,-2.00395921265,0.528798509498,-0.262713262347,-0.0607792128382,1.87042531239,2.48288465884,0.634489305269,-0.55767941955,0.677578141189,-0.887467307797,0.984117156286,-1.31142831913,-0.210452819798,-0.353972474402,0.346883908443,0.295763368478,-0.211673016698,-0.0694738587017,-0.143191593437,-0.600571256407,-0.184094777243,0.113060113209,0.252251044697,0.367815316816,0.773426071475,0.390743253324,0.346018520581,-0.141977479594,-0.201911108916,0.372768947023,-0.429490262955,0.0151328283899,-0.0104002025017,-0.0220317441965,0.063118481661],[-33641.74518,-937.904373382,700.096633939,-1520.46418084,2617.19307326,2380.89348445,-514.818108723,-1640.15414239,-229.677062002,-866.478412458,-470.92208828,1106.03992636,-378.569939344,142.865398785,-301.220471685,53.4938123002,-184.06802615,835.673541233,120.87473281,-204.280483118,117.780006523,-430.518751921,-218.24402813,-176.496216292,47.5503294098,-67.2064072837,-25.1894882307,195.465953555,54.955399654,81.6871461591,-184.871348904,-5.23389578839,-89.0693615664,-138.216907829,-117.166909153,-12.1180548379,-10.7127228814,19.478186801,-49.9293630919,27.1021135931,38.6612297128,-52.615980741,-17.3031944889,-24.7781109224,-9.18201702068,-70.7622623583,-25.5637117401,-24.5682969324,8.50021087672,-8.72458660113,1.82529792904,-4.10829684483,-1.83623125749,-0.653556294195,2.27727042449,5.81965753113,0.611602294721,-0.505885130095,-7.53190847261,-4.39890253874,-18.6756487021,3.91650287441,-6.56173535933,3.20178605173,0.988409678257,-2.66893264061,-5.8829172084,-0.814205954119,-1.11954505836,-1.54894322927,1.95362553665,2.90925866288,3.05404742539,3.42244352208,1.59708747787,-3.75340067021,2.51855684171,-3.69803882295,1.47281265964,-4.66250605755,1.60459066639,0.145021784334,0.176532834091,-1.05097782238,-0.904256107646,-1.92185705913,0.558162478282,-0.154521135497,-0.0891000330856,1.89354867709,2.36194514254,0.601698235962,-0.648245615578,0.660973594777,-0.937607429781,0.950121319848,-1.26785128896,-0.179388382859,-0.382460065201,0.351097961159,0.284119490618,-0.204646589683,-0.071411383656,-0.122866765131,-0.582638442597,-0.171907147474,0.134261415567,0.238722541777,0.370234017117,0.744701628578,0.392103645623,0.303644201072,-0.154176450261,-0.236180333592,0.366029104752,-0.398849510893,0.00793879847893,-1.96794605075e-05,-0.0296925675265,0.0669678451843],[-33490.7632917,-1025.01195442,800.678464622,-1569.76870951,2626.04456971,2403.93471644,-585.53110452,-1647.13789553,-239.41278736,-856.828667419,-461.885805535,1124.06371939,-377.375763556,158.595546518,-288.134582402,60.1183095593,-163.914044755,823.987080294,135.036571796,-211.61057143,114.852607215,-429.231158335,-235.627500286,-183.831737212,48.3970984879,-64.9761117371,-21.590219597,192.413367347,52.955656004,70.4101605988,-191.520799012,-16.8138882561,-95.6672876816,-138.607230307,-110.970350975,-11.9268663291,-10.4872617583,19.2733714005,-48.1766914901,26.2285546915,37.3762644359,-54.1664005488,-22.7194222643,-26.3174775491,-10.3046644245,-69.7910057878,-22.7036786216,-22.325593103,8.2200727996,-8.81713579632,2.03745196875,-3.87217493253,-1.57711116884,-0.601528764775,1.65862852626,5.18992006171,0.410506232397,-1.43167458633,-7.18490507733,-3.21510764842,-18.8621093572,3.09347856585,-7.67253473449,2.94435360217,0.829296022909,-2.51557564054,-5.88226201685,-0.605798939312,-0.949780420402,-1.55405708631,1.99127141986,2.69072733322,3.05738663517,3.19767254315,1.69027077532,-3.78844410203,2.43199482566,-4.09642506081,1.4531225845,-4.75601446944,1.54810178773,0.0910863165144,0.213108563067,-1.0431854957,-0.840513947497,-1.83959339351,0.585484948367,-0.0425786568502,-0.11815763835,1.9182244479,2.23063678495,0.564637267251,-0.725308594209,0.644293057181,-0.962170383476,0.908812667633,-1.22428257887,-0.143014810762,-0.417731616033,0.354852894567,0.272821627402,-0.197845128907,-0.0747761029227,-0.10092759542,-0.565981128652,-0.157994709506,0.15540259911,0.226364395512,0.373129673847,0.712781252225,0.395564620122,0.261245639465,-0.167702250903,-0.267216566531,0.357670549827,-0.363795366708,-0.00237724111679,0.00946545668621,-0.0373638780724,0.0719952165825],[-33354.9422407,-1127.62634912,906.331037619,-1612.90955765,2635.97931081,2421.1219386,-671.654325929,-1639.70577009,-246.18939117,-842.837634629,-459.559677713,1141.25722504,-374.047773942,168.541243881,-273.089263882,66.409200454,-141.871883338,808.491945176,151.786601599,-222.098952715,110.722501012,-427.652628258,-250.918066233,-189.555659131,48.7401936415,-62.3304593453,-18.5341078126,190.190303412,49.8191456356,58.90626509,-197.959223784,-27.4928332983,-101.889478285,-136.752278145,-103.606572795,-11.6889536995,-10.4140536393,19.0068196419,-45.8187408396,25.0288993285,36.3651412359,-55.8309683042,-28.1090219112,-27.9749216444,-11.001464871,-68.42087547,-19.7621687952,-19.5606261534,7.96297715437,-8.92541517843,2.27835638061,-3.59481000859,-1.36159557277,-0.4123642366,0.909591842181,4.63336859921,0.0818589540294,-2.30219157422,-6.66621762388,-1.98141529693,-18.8883427195,2.19313569536,-8.6917756563,2.68613432556,0.66903599636,-2.35151713038,-5.89701027189,-0.390472228422,-0.744314228413,-1.57097187984,2.04000170165,2.43047138674,3.07027713317,2.98473034948,1.76437152388,-3.73479817958,2.34537564409,-4.44810114085,1.41893473989,-4.88111750765,1.49098704559,0.0369067796811,0.251653992694,-1.04109146449,-0.77033551893,-1.75830037555,0.610062313238,0.0716324383136,-0.147947762742,1.94491604711,2.08870316431,0.523119392741,-0.787197158795,0.629439853563,-0.959397293683,0.860682502713,-1.18026708925,-0.100330936001,-0.460373468694,0.357899466037,0.262029707379,-0.191330344185,-0.0792721594411,-0.0775464503317,-0.550602494554,-0.142488078711,0.176006070545,0.215132399471,0.376576360687,0.677545421215,0.401105860925,0.219160922391,-0.182074642203,-0.294466151618,0.348069256251,-0.323856385604,-0.0156725857192,0.0177645225666,-0.0448368678177,0.0783507715982],[-33234.7079091,-1247.69409937,998.480011985,-1647.9170107,2645.55477307,2428.21480577,-767.738863541,-1621.64634088,-248.833783504,-826.03396626,-463.973292109,1158.60713253,-369.62121498,174.548079666,-256.112795953,72.7408970349,-118.204602749,789.565110032,170.836081106,-235.808029154,106.252363788,-425.757247424,-263.183392776,-193.446201781,48.6747372696,-59.2083638933,-15.893398021,188.627339217,45.6426534527,47.2884211716,-204.031292907,-36.8864268087,-107.634554286,-132.461801028,-95.0608647136,-11.3656548934,-10.4536086037,18.6953979888,-42.8990731056,23.5503831441,35.5886550595,-57.5846697265,-33.3760707816,-29.7108902275,-11.2331998098,-66.638838331,-16.7023251535,-16.2723733764,7.73115440544,-9.02829385153,2.54211940047,-3.28124102353,-1.18680063461,-0.104314194021,0.0373878884433,4.15673329341,-0.377121036085,-3.1028268573,-5.96478670898,-0.690777972069,-18.7583577699,1.21715694634,-9.61293894177,2.42648740332,0.513898930264,-2.18019126276,-5.92238556359,-0.169607127639,-0.510206337657,-1.59886681469,2.09602686292,2.12836745324,3.09241740347,2.78480780303,1.82001158232,-3.59163197212,2.26457743463,-4.75253786821,1.37028805637,-5.04071052247,1.43236270781,-0.0166618590403,0.290930698657,-1.0420720029,-0.694419618983,-1.67858439651,0.631301602773,0.185606179007,-0.178220377403,1.97297248934,1.93597568625,0.476592811472,-0.833434767732,0.61867475712,-0.929168570673,0.806477633484,-1.13602209422,-0.0503742208396,-0.511079211418,0.359785454643,0.251547331418,-0.18515134596,-0.0842461681651,-0.0530236328964,-0.535980218847,-0.125534084157,0.195546568837,0.205007627878,0.380320916468,0.63900505812,0.408425131885,0.177577624118,-0.196741711184,-0.317797133903,0.337771731209,-0.278908891387,-0.0316965931953,0.0244025618774,-0.0518790789748,0.0861064743393],[-33127.0960757,-1375.79039121,1070.49506417,-1675.55280234,2656.28273189,2424.20957809,-867.271226106,-1595.64886587,-247.353685769,-807.894445545,-474.724206596,1177.19321336,-364.522863598,178.523448636,-237.261342795,79.2747901604,-93.4288902649,767.591223115,191.812126832,-252.563427412,102.289105274,-423.450523233,-271.572379642,-195.347264429,48.2982372522,-55.6292707743,-13.5848946532,187.512666492,40.5835126535,35.6242237353,-209.52036642,-44.6568709969,-112.814158769,-125.56139707,-85.3870674108,-10.9053958336,-10.5808958503,18.3427161183,-39.4813848603,21.8482443145,34.9850461469,-59.3801151029,-38.4386931283,-31.4796899575,-10.9699112393,-64.4566509333,-13.4908779674,-12.4707436242,7.53025545359,-9.10484180703,2.82101517663,-2.93895191844,-1.05116695183,0.298948275521,-0.944047533787,3.75922472127,-0.965624807951,-3.82199347539,-5.07558156373,0.659799648407,-18.4818006769,0.166627126082,-10.4301864496,2.16524547126,0.37097719273,-2.00460234218,-5.95325553889,0.0537336143061,-0.255361814746,-1.63649131908,2.15390759722,1.78628247882,3.12169444417,2.59834952174,1.85717770705,-3.3605272743,2.19496364386,-5.01010980143,1.30688703487,-5.23775147679,1.37135425163,-0.0685310979477,0.329894818145,-1.04334244851,-0.613918095998,-1.60082454055,0.648394996445,0.296576669095,-0.208359000006,2.00102584742,1.77260465654,0.424211311049,-0.863994277444,0.613965057142,-0.87215594314,0.74677051588,-1.09208300403,0.00758836096493,-0.570507649977,0.360043820259,0.241188419211,-0.179308502338,-0.0890216237694,-0.027723480876,-0.521461765278,-0.10741051313,0.213500198048,0.195990621956,0.383896055907,0.597301353521,0.417027370592,0.136633083203,-0.211218043572,-0.337253944196,0.327309863317,-0.229044247815,-0.0501976611012,0.028794645743,-0.0582473272458,0.09527044267],[-33029.9204025,-1506.91186157,1125.91057725,-1697.14917116,2668.87824982,2410.74972435,-965.869331924,-1563.35534753,-241.901689545,-789.761791702,-491.094017725,1197.15490247,-358.591233906,181.713847214,-216.551089134,86.1447578172,-68.0459894721,742.933881492,214.15047729,-272.012438074,99.4042402847,-420.522397573,-275.485343942,-195.137408252,47.7097424325,-51.5980033038,-11.5744452188,186.630681199,34.8436329558,23.8919206059,-214.144837206,-50.5860360645,-117.332319714,-115.919532024,-74.6934527869,-10.2582079556,-10.7718577834,17.9392811741,-35.6254578856,19.9807496759,34.4748222989,-61.1488542278,-43.2484943632,-33.2222926902,-10.2053458242,-61.9046464145,-10.1055974988,-8.1724161219,7.36526511947,-9.13629967069,3.10587596906,-2.57222625093,-0.954963651473,0.773708072059,-2.0158334518,3.431905628,-1.67812602256,-4.45507173625,-3.9973162772,2.065093837,-18.0706570377,-0.959468300044,-11.136839984,1.90244128346,0.246692113103,-1.82744295233,-5.98369020316,0.274901399053,0.0133110405231,-1.68252552438,2.20756152748,1.40817923476,3.15345729178,2.42562119709,1.87395293811,-3.04425353597,2.14004292722,-5.2213689801,1.22776595603,-5.47473276087,1.3072875515,-0.117720244452,0.367721675998,-1.04226335979,-0.530391955108,-1.52499258345,0.660251245038,0.401939370741,-0.237464781487,2.02702780547,1.59917900791,0.364615387492,-0.878993967047,0.616540002622,-0.789620203643,0.68183652112,-1.04908661938,0.0739811271356,-0.639124208836,0.358267112792,0.230789434533,-0.173749357007,-0.0930093734571,-0.00208037467847,-0.506327164536,-0.0885191903045,0.229424161615,0.188071710982,0.3866958651,0.552699156159,0.42622939948,0.0964949855577,-0.225183289088,-0.352940836484,0.317132575065,-0.17449674073,-0.0709614913227,0.0303323496775,-0.0637085478512,0.105799035143],[-32943.3270903,-1640.43304076,1171.37282654,-1713.7005026,2682.95229952,2390.17983929,-1061.423275,-1526.23741408,-232.406404468,-772.782621181,-512.226939925,1217.77765056,-351.469559235,184.585459706,-194.139606929,93.5077654703,-42.4821304168,715.957719522,237.166986316,-293.766236052,97.8367555537,-416.73467762,-274.596899075,-192.803873105,47.0019685119,-47.0884788037,-9.85888554594,185.78067524,28.6347194017,11.9894485691,-217.598567936,-54.568719648,-121.120377354,-103.434592984,-63.143107361,-9.38204396318,-11.0022352327,17.4651120844,-31.3809362675,18.0042270204,33.9696174695,-62.8124108081,-47.7861813856,-34.8755311026,-8.94859571241,-59.0309727988,-6.53493225192,-3.40098604516,7.23952058242,-9.10689643734,3.38576988719,-2.1819616434,-0.900063294742,1.29950422864,-3.15623886889,3.16056767558,-2.50539237686,-5.00012803585,-2.73322432359,3.51227855941,-17.5390825782,-2.16438207299,-11.7251793172,1.63863427678,0.146352103635,-1.65137668449,-6.00715558627,0.488228716189,0.290646297422,-1.73553769582,2.25128443347,1.00011844826,3.18171632554,2.2663659038,1.86708465918,-2.64660863535,2.10134530322,-5.38694704226,1.13158371113,-5.75351269494,1.23983027466,-0.16341065811,0.403795713096,-1.03648620437,-0.445592105121,-1.45067172685,0.66559010774,0.499435737892,-0.264312145328,2.04853253338,1.41670372541,0.296286477143,-0.878672595562,0.626946107566,-0.683484866424,0.611792720253,-1.00772612182,0.14888237035,-0.717101429562,0.35413782685,0.220227581816,-0.1683499826,-0.095746974089,0.0234315849738,-0.489878556052,-0.0693359891413,0.242971282208,0.181244290498,0.388051331222,0.505583640577,0.435269703201,0.0573723941211,-0.238437468035,-0.365003380701,0.307648141138,-0.115632533105,-0.0938005751624,0.0284256595391,-0.0680404073639,0.117589429762],[-32869.548906,-1775.74053872,1211.9635581,-1725.95353988,2697.96934619,2364.35604715,-1152.77093402,-1486.39887021,-218.659816548,-757.850503627,-537.235350925,1238.1317572,-342.998944949,187.203654016,-170.455478391,101.514674144,-17.0747555475,687.035616315,260.200182521,-317.481657874,97.6311276317,-411.901064042,-268.791554285,-188.422425719,46.2532258184,-42.0682281315,-8.44369800013,184.7852359,22.159268642,-0.220715894953,-219.582772533,-56.5726258733,-124.137695347,-88.0305907189,-50.9462390067,-8.24515860068,-11.2536888806,16.8933311321,-26.790961387,15.9733987756,33.3791349463,-64.2920023143,-52.0468843744,-36.3743334188,-7.21977841333,-55.8955647946,-2.776035067,1.81109139826,7.15503886344,-9.00513117622,3.64815206185,-1.76885185788,-0.889241035195,1.859025038,-4.34172909632,2.9285955809,-3.43569065033,-5.45427053886,-1.29008553834,4.98267351052,-16.9038201053,-3.45280165128,-12.1860955958,1.37535810836,0.0738894734034,-1.47912783193,-6.0173631101,0.687549628637,0.572581507695,-1.79406816646,2.28029282937,0.569505230697,3.20035091005,2.11971248223,1.83290784891,-2.17279709516,2.07887292263,-5.50725201777,1.01669003159,-6.07497017424,1.16904929406,-0.204848423376,0.437631056647,-1.0240616535,-0.361377589485,-1.37721708691,0.663039708033,0.587117142625,-0.287512598704,2.06303245943,1.22652496659,0.217961241215,-0.863434724924,0.645303878284,-0.556331538767,0.536628732487,-0.968642405489,0.232020816862,-0.8042657613,0.347454751823,0.20946100217,-0.162923408267,-0.0969009423628,0.0483182112611,-0.471508245094,-0.0503683546256,0.253865449806,0.175482063502,0.387313229694,0.456413670439,0.443405587516,0.0194976079667,-0.250805883012,-0.37362120827,0.299219830638,-0.0529226196126,-0.11852378675,0.0225104838671,-0.0710214563222,0.130478019399],[-32809.5187686,-1908.04443987,1249.20098025,-1734.33760164,2714.85945865,2334.88804685,-1238.58586797,-1446.13773447,-200.478901084,-745.291797668,-565.079401172,1257.51897674,-333.18575702,189.604533613,-146.21128901,110.258591448,7.98027224469,656.544597158,282.737425358,-342.843709686,98.8536964235,-405.894387755,-258.055124818,-182.090445319,45.5270119279,-36.5119111672,-7.3320360144,183.519113487,15.6174582262,-12.8616218527,-219.804887927,-56.6055214991,-126.334724523,-69.6768138934,-38.3378119203,-6.82681207641,-11.5172968831,16.1919234137,-21.8904388845,13.9435982062,32.6149960685,-65.508071244,-56.0256361976,-37.641881849,-5.05455695685,-52.562384885,1.1650695423,7.41810371744,7.11224988223,-8.82437472129,3.87906015659,-1.33484524082,-0.925393086978,2.43780299338,-5.54584195829,2.71966584802,-4.45385057611,-5.81374144384,0.324914630809,6.45255161515,-16.1831838268,-4.82877415573,-12.5071546061,1.11499548644,0.0317260395942,-1.31343645865,-6.00868369052,0.866532599695,0.855642734006,-1.85649977463,2.29084749773,0.124883686928,3.20348569946,1.98511205057,1.7679063938,-1.62958354059,2.0715034648,-5.58178432964,0.880643776551,-6.43868311883,1.09532315107,-0.241329620475,0.468824265719,-1.00349620886,-0.279723708714,-1.30382754446,0.65121625938,0.663271963164,-0.305630732786,2.06818329888,1.03042923241,0.128808508507,-0.833795997394,0.67149588933,-0.41114602402,0.456114315631,-0.932320766655,0.322804004582,-0.900073639819,0.338139734019,0.198517713517,-0.15724771302,-0.0962596917283,0.072063161118,-0.45069444784,-0.0321375427009,0.261885104942,0.170710277481,0.383916581512,0.405710321146,0.449939320494,-0.016815979094,-0.262065728568,-0.378929286904,0.292083785349,0.0130828728674,-0.144939323763,0.0120617689147,-0.0724307529717,0.144264411089],[-32762.887756,-2030.66533638,1282.27583147,-1738.28955906,2735.28923605,2303.45987577,-1317.47134969,-1407.21136387,-177.50375719,-734.952579011,-594.57023377,1275.31845771,-321.999650216,191.668513696,-122.338147285,119.831380053,32.6314725902,624.844201049,304.362995181,-369.554988645,101.592219085,-398.640525711,-242.431817235,-173.873828943,44.8843513846,-30.3822199923,-6.52221789976,181.901557948,9.20402783175,-26.0374164307,-217.983213354,-54.7130035897,-127.630021265,-48.4140950855,-25.5585714934,-5.11585563508,-11.786067488,15.3292316717,-16.7062840963,11.9683420095,31.5900568322,-66.383142848,-59.7154130172,-38.586017805,-2.5123085752,-49.0924604065,5.27254303168,13.360360815,7.10893901307,-8.56030596373,4.06415824115,-0.882287000416,-1.01109229005,3.02437139175,-6.73983808648,2.51819664222,-5.54162927031,-6.07559856087,2.10599779675,7.89247672909,-15.3951713095,-6.29517658282,-12.671612135,0.860212423438,0.0212868071394,-1.15682799466,-5.97564039268,1.01920619464,1.13697091372,-1.92087149747,2.28008961609,-0.324426048772,3.18517538764,1.86275725441,1.66859149846,-1.02515386936,2.07682189806,-5.60888799055,0.719831519151,-6.84260124366,1.01915826908,-0.272214209796,0.497047059175,-0.973604019053,-0.202464865822,-1.22956286872,0.628855642728,0.726398089808,-0.317309513054,2.06180392728,0.830646381347,0.0283973398297,-0.790370894389,0.705096642482,-0.251246822321,0.369676809082,-0.899028988262,0.42033950765,-1.00361892532,0.326185857932,0.187429104906,-0.151093053485,-0.0937006639157,0.0941627686749,-0.426985936055,-0.0151271100287,0.26687163423,0.166808012036,0.377407733091,0.354027078331,0.454195646795,-0.0511429164441,-0.271943812785,-0.380966675754,0.286264009365,0.0817365796553,-0.172848294199,-0.00342650729516,-0.0720585818155,0.158714266157],[-32731.1573686,-2141.30906065,1306.93392802,-1735.96043458,2759.29745141,2271.05179549,-1388.30726339,-1371.9686064,-148.887387401,-726.547414122,-624.627220029,1290.72616551,-309.724024185,193.07097959,-100.095663202,130.438394635,56.9269036397,592.236389664,324.690764124,-397.460331888,105.931867582,-390.189014322,-222.032096686,-163.83874171,44.4137649013,-23.6048239247,-5.99900860018,179.875386796,3.07601781105,-39.8380189719,-213.893173366,-50.9784820508,-127.929845672,-24.3511922501,-12.8461016057,-3.1042768066,-12.0420137052,14.283538643,-11.2602442536,10.0932681544,30.2190203038,-66.8553853045,-63.1071326307,-39.1070013512,0.325771300095,-45.5397359,9.52225505878,19.5666098981,7.14026804846,-8.20682989217,4.19207725907,-0.413759465427,-1.1470554889,3.61011015433,-7.89666740637,2.30972085781,-6.6807149576,-6.23665703743,4.04859285935,9.26748109166,-14.5563232748,-7.8536511901,-12.658378899,0.613268639548,0.0436943203059,-1.0108852947,-5.91252323188,1.14096407127,1.41418856512,-1.98519436743,2.24616660775,-0.769304241854,3.1398168039,1.75316611215,1.5317011624,-0.368931125423,2.09091852169,-5.5856804244,0.529564855368,-7.28254888683,0.940854075143,-0.296929361635,0.522074774295,-0.933393288534,-0.130873920989,-1.15341151947,0.594959566417,0.775284304766,-0.3215123195,2.04193126017,0.629755371644,-0.0832707172989,-0.733837912503,0.745248936896,-0.0804179369496,0.276391300758,-0.868772524378,0.523353066558,-1.11360033828,0.311564078631,0.176173271746,-0.144261949926,-0.089158936103,0.114212873234,-0.400020983794,0.000316360928572,0.268724647628,0.163583361205,0.367458991026,0.301897258422,0.45552883351,-0.0829393187271,-0.280144998716,-0.379684335144,0.281545512759,0.152260649791,-0.202021415997,-0.0244516312213,-0.069695784291,0.173539147136],[-32719.2957585,-2240.0849482,1320.61300259,-1725.65381936,2785.20975711,2238.74267641,-1450.31380375,-1342.26661799,-113.890639392,-719.779013068,-654.272320855,1302.70349762,-296.457712917,193.178307319,-80.7095058362,142.215133219,80.9148595339,558.876080797,343.355809461,-426.425014778,111.897477173,-380.562073886,-197.078951228,-152.061399914,44.2013515629,-16.1078507888,-5.76171319872,177.399357642,-2.63435374429,-54.3503626779,-207.338445189,-45.5483954554,-127.130178697,2.32828428169,-0.429992602205,-0.78661055871,-12.2683148301,13.036937303,-5.57195260908,8.35147867427,28.4146022088,-66.873748767,-66.1992789299,-39.0962000149,3.35316243105,-41.9501031329,13.881156291,25.9542724334,7.20123672477,-7.75938634772,4.25340393473,0.0661609813302,-1.33526246383,4.18851130088,-8.99141353615,2.07866040486,-7.85230592499,-6.29482450568,6.14784012242,10.5361979252,-13.6811376828,-9.50443013158,-12.4419622976,0.377054965814,0.0991692442299,-0.876522140572,-5.81383041209,1.22746384469,1.68529441941,-2.04773982162,2.18769781283,-1.20076529568,3.06150860585,1.65673928576,1.35387265411,0.328212474559,2.10814685717,-5.50824271227,0.304272804686,-7.75180707035,0.860742536611,-0.314943837216,0.543768326023,-0.882241785995,-0.0659749211988,-1.07429981188,0.548636892173,0.808928714434,-0.317531636896,2.0065278984,0.430623337596,-0.205925962862,-0.665106015361,0.79055267862,0.0968405643821,0.175097817317,-0.841286164108,0.630118370754,-1.2282876481,0.29427726606,0.164745309642,-0.136572597491,-0.082659989265,0.131840846775,-0.369530175802,0.0139052018361,0.267406133747,0.160763271138,0.353796513057,0.249822731547,0.453258839772,-0.11158667404,-0.286366170895,-0.375003586982,0.277491460654,0.223690443826,-0.232184225647,-0.0515079555335,-0.0651267020613,0.188384113849],[-32731.461217,-2324.88088601,1325.60863391,-1705.85143297,2811.19229094,2208.54232698,-1503.02735504,-1318.27950599,-72.1817116643,-714.158279529,-682.505907447,1310.11886967,-281.666639279,191.05901841,-64.8781889123,155.116057064,104.633309479,524.809344713,360.035786268,-456.1842558,119.437777121,-369.60132468,-167.933467084,-138.613806101,44.3023027388,-7.84937002262,-5.8184657099,174.45344884,-7.7943471995,-69.6551855589,-198.114438758,-38.6368783015,-125.107833277,31.3522964629,11.465144242,1.8358307071,-12.4565385448,11.5754042007,0.335549718338,6.76844845427,26.0862109989,-66.3913244491,-68.9968280495,-38.4323303509,6.43405667968,-38.3609806652,18.3025949036,32.4285438396,7.28772468934,-7.21710919733,4.23988281283,0.548927722935,-1.57860272574,4.7537865547,-9.9991845457,1.80705668811,-9.03539739648,-6.24955405813,8.39755937915,11.6493869248,-12.7818943027,-11.2460081884,-11.9928535134,0.155603915943,0.186752359616,-0.754305411589,-5.67491118882,1.27442990517,1.94801714552,-2.10692594685,2.10330555006,-1.60947162776,2.94389395438,1.57360360154,1.1313549321,1.05365846307,2.12107431775,-5.37162654839,0.037839609926,-8.24090946799,0.779284249624,-0.325672732309,0.561982170955,-0.819951858873,-0.00869687887369,-0.991260487585,0.489220782866,0.82631226308,-0.304928438999,1.95333159531,0.236441424546,-0.339097792229,-0.58538819659,0.839021491489,0.275186721318,0.0645174491312,-0.816096265366,0.738366866716,-1.34549901121,0.274382123803,0.153195599103,-0.127885424733,-0.0742999005775,0.146677269799,-0.335381958353,0.0254065460719,0.262883906049,0.15801508779,0.336124739408,0.198293271885,0.446627207127,-0.136425720751,-0.290299075069,-0.366863367012,0.273461281509,0.294819936985,-0.263009724073,-0.0850881005958,-0.0581141230388,0.202818685601],[-32767.1885534,-2388.44534311,1330.94576147,-1674.73227697,2836.57061111,2184.06245949,-1546.17145502,-1298.04246475,-23.8323592845,-708.915053961,-708.126459982,1311.81575695,-264.071908881,185.467073957,-52.5677028417,168.868231405,128.11368756,490.034842122,374.463374588,-486.254823311,128.418182059,-356.92010245,-135.111985782,-123.576965284,44.7249066877,1.17270796678,-6.17439460554,171.044781158,-12.2552382235,-85.8267308697,-186.001475322,-30.5361441103,-121.718510159,62.34592567,22.6225002246,4.75106473001,-12.6076852956,9.89042291954,6.42859617036,5.36844438495,23.136236853,-65.3656756021,-71.5118543939,-36.9798579192,9.40115270399,-34.8004622546,22.7241011097,38.8789823842,7.39608144127,-6.58385831877,4.14426977464,1.02030911971,-1.88011288821,5.29930044005,-10.8936385696,1.47275747916,-10.2059234236,-6.10218630788,10.7891174518,12.5490625938,-11.8689157887,-13.0749130154,-11.2778698111,-0.0457754250522,0.30420259777,-0.644729082148,-5.49237412726,1.2779515887,2.19917847212,-2.16101973191,1.99112163101,-1.98542915576,2.77995449573,1.50346045904,0.859868913958,1.79270046174,2.12013911262,-5.16997888951,-0.276104814054,-8.73745701267,0.697063210154,-0.328453855526,0.576478518541,-0.746761851585,0.0401320596171,-0.903519248136,0.416476919037,0.826186432696,-0.283539916614,1.87973840273,0.0506867738503,-0.482157550566,-0.496302828883,0.887941847282,0.448262824808,-0.056648936666,-0.792589186934,0.845225432454,-1.46256796258,0.25198706383,0.141634332008,-0.118118689001,-0.0642178245679,0.158355923772,-0.297616473361,0.0346620107411,0.255106417527,0.154948319956,0.314069676195,0.147795558586,0.434763583578,-0.156794363295,-0.291647663891,-0.355270198702,0.268605970542,0.364131532218,-0.294108300557,-0.125678868284,-0.0483866437212,0.216336411545],[-32826.053789,-2424.07814862,1354.7594578,-1630.93855437,2859.62070704,2170.10642498,-1580.58020218,-1277.92223488,30.782742322,-703.569748444,-729.870644482,1306.33874616,-241.98899306,174.939504767,-43.0125836951,183.094731283,151.31682127,454.496759563,386.341362626,-516.034253827,138.592557638,-341.978725456,-99.3036003552,-107.057053021,45.4650118292,10.9299003672,-6.83142101093,167.197929862,-15.8822007242,-102.91610614,-170.811438632,-21.6039723747,-116.810346293,94.8202367629,32.8220000545,7.94166637242,-12.7229491423,7.98389844582,12.6591900819,4.17294609415,19.4640923776,-63.7725596046,-73.7576950246,-34.593748424,12.058489173,-31.2881936009,27.0685638558,45.1809804268,7.52321865759,-5.86579284773,3.96264124826,1.45997901336,-2.24213126231,5.81820052987,-11.6483863202,1.05113791709,-11.3371608537,-5.85272782132,13.3097750759,13.1701187639,-10.9500285251,-14.9851842163,-10.2610614717,-0.220724666627,0.448596695239,-0.547556239734,-5.26405347377,1.23518568912,2.43487339303,-2.208065259,1.84968971631,-2.31787999083,2.5632545794,1.44577510339,0.535612292803,2.52877678085,2.093765179,-4.89652024938,-0.643757615934,-9.2259671015,0.614605173383,-0.322415997544,0.587028554417,-0.663300698663,0.0800338713919,-0.810466096493,0.330779692991,0.807306155927,-0.253469906796,1.78315915313,-0.122656929518,-0.63395774198,-0.399764462353,0.93387030815,0.608667401925,-0.189602225311,-0.770026931785,0.947178978625,-1.57629881112,0.227190274008,0.130228651766,-0.107248852875,-0.0525799968223,0.166578362022,-0.256479293496,0.041635578693,0.244074922848,0.151127911021,0.287264330313,0.0989053897054,0.416755092974,-0.171973444637,-0.290112627151,-0.340262638422,0.261906994238,0.429757266627,-0.324974414236,-0.173747526668,-0.0356230880331,0.228349035896],[-32911.9509611,-2427.10015602,1395.99764287,-1573.24897319,2876.44642548,2165.09375407,-1605.92506261,-1261.94215761,91.4652669942,-698.356361189,-747.646211993,1292.70280398,-216.597646314,159.376118469,-36.5236943424,197.565216878,174.073568977,418.073562059,395.471392593,-545.521782311,150.179196571,-324.922000408,-60.949983962,-89.5182496847,46.5770725093,21.3878239221,-7.74553209419,162.96529969,-18.6518296808,-120.789011218,-152.643902015,-12.0474700947,-110.380845341,128.282203948,41.7888100476,11.3960736575,-12.7843368107,5.88984543077,18.9550963312,3.20476576638,14.9931147321,-61.6587887081,-75.6783985877,-31.1710182774,14.2489792023,-27.8594288822,31.2752037859,51.1964724607,7.66691793459,-5.0647502572,3.70007762762,1.83989928312,-2.65854505726,6.3035582283,-12.2410465256,0.530229294285,-12.4106992819,-5.47467745865,15.9331908541,13.4593387729,-10.0299936987,-16.9618582273,-8.90254339672,-0.362975722373,0.617904100582,-0.460827144606,-4.98891644409,1.1469318273,2.64945594986,-2.24477165885,1.68022228859,-2.59676957264,2.29478670721,1.39779509713,0.162934717461,3.24379668046,2.03221788099,-4.54228206677,-1.06929418478,-9.68698876821,0.531816094028,-0.306297163442,0.593462391518,-0.570316986765,0.111477067063,-0.711998603374,0.233864102491,0.768406214187,-0.215151557728,1.66221597144,-0.279269506532,-0.790600919871,-0.297779881968,0.974265336939,0.748505594224,-0.334414926606,-0.747091577242,1.040235847,-1.68266573473,0.199919072744,0.119140152778,-0.0953714677576,-0.0394835642239,0.171216189807,-0.212478161731,0.0466020289602,0.229728491454,0.14616516024,0.255395301254,0.052342349829,0.39207253409,-0.181130923281,-0.284864616861,-0.321715747767,0.252613582493,0.489655321501,-0.354772740948,-0.229539100644,-0.0193987387645,0.238251685931],[-33026.3623712,-2394.34550863,1433.26959368,-1498.6292887,2882.66944782,2161.05054819,-1621.96722839,-1262.53861478,158.528572956,-693.281445222,-762.510903997,1270.3675514,-191.913614857,139.653098273,-34.9895051405,212.178355391,196.389460211,380.603809368,401.852138948,-575.260008639,163.618347327,-306.804960808,-20.299174112,-71.9877009668,48.1345041032,32.5748914195,-8.85559632215,158.515187885,-20.6289268144,-139.160802339,-131.937955447,-1.92306833185,-102.680026597,162.260231381,49.157580765,15.086876365,-12.7471419409,3.66258065793,25.2476988755,2.49441665815,9.67523352422,-59.1422805806,-77.1515199497,-26.6795197077,15.8692873861,-24.5779567709,35.3055783347,56.7709135007,7.82067528557,-4.18221567404,3.36761736465,2.13215435725,-3.1135879369,6.75236496675,-12.6475485446,-0.0912971087,-13.420475926,-4.9093543221,18.6127160097,13.3804460563,-9.11364616596,-18.9781301681,-7.15900835891,-0.467296409572,0.808649732175,-0.381729475099,-4.66602971743,1.01711323233,2.83779960614,-2.26435712318,1.48629641847,-2.8116808973,1.98419696042,1.35333610026,-0.243256066635,3.91711553502,1.92914608518,-4.09566729471,-1.55419777677,-10.0965410872,0.448049180005,-0.279196558491,0.595536563903,-0.468837914362,0.135466195972,-0.607897795814,0.12940986306,0.708161396623,-0.168640962319,1.51677400919,-0.414510291323,-0.944702939576,-0.192731333175,1.00808577869,0.859419914341,-0.489837412782,-0.721725060842,1.11987657775,-1.77672548253,0.170053711746,0.108366885237,-0.0827148412614,-0.0251184429916,0.172154151083,-0.166270222499,0.0501552460709,0.211977470181,0.139979646641,0.218099659213,0.00906435975504,0.360703908753,-0.183397835822,-0.274320531614,-0.299332629694,0.240342777051,0.541665570879,-0.382254156328,-0.293032063549,0.00084311271568,0.245425654884],[-33169.5774874,-2327.65716524,1463.07744315,-1404.03057307,2873.08394808,2152.99809088,-1631.88972707,-1289.86215802,232.116381847,-688.177578635,-775.198311803,1238.33396064,-171.079885272,116.219183439,-39.4432049641,226.79130843,218.408157059,341.992962709,405.481470607,-605.49507032,178.923158475,-288.591757702,22.0342869313,-55.6088134395,50.1895424455,44.5459238947,-10.1451448379,154.121246818,-21.8681561473,-157.755576872,-109.201580617,8.6080460249,-93.9903006766,196.134653701,54.5171183564,18.9602392055,-12.5535614074,1.35058964084,31.4688169252,2.07288467891,3.4635864234,-56.3656032187,-78.0715608507,-21.0869765691,16.7808218883,-21.5037495607,39.1028884258,61.7352310706,7.97340060543,-3.2250016838,2.97626097037,2.30909377679,-3.5898777486,7.16247911626,-12.8392478262,-0.82424535925,-14.3564590157,-4.09744369941,21.2924756493,12.8909591675,-8.20632191983,-21.0015767898,-4.98735718886,-0.528809250074,1.01456199201,-0.307477707315,-4.29500990814,0.85004838636,2.99589039783,-2.25870692158,1.27139041995,-2.94974555193,1.64189946799,1.30624292456,-0.66643148899,4.52526890177,1.77693302158,-3.54404476067,-2.09840549942,-10.4266890444,0.362551194816,-0.240699827415,0.592981624209,-0.360361648397,0.152871242373,-0.497499723401,0.0222896056332,0.625359846986,-0.113917376637,1.34670669821,-0.522726273985,-1.08795402162,-0.0874220553017,1.03361144317,0.931843945142,-0.654315791974,-0.691755107832,1.18067288895,-1.85280662413,0.137591646288,0.0977978201571,-0.0695713563921,-0.00982531263979,0.169212690389,-0.118603942701,0.0530062107068,0.190921564179,0.132589259836,0.174951341176,-0.0296869130683,0.322632281694,-0.177882670942,-0.256862521762,-0.272880057614,0.224607592168,0.583191697982,-0.405929899602,-0.364098621525,0.0257287009099,0.249162155324],[-33341.7754895,-2227.76626072,1503.28260569,-1289.05096687,2843.64615825,2140.49594,-1639.83977691,-1349.37707184,311.147478845,-682.793286009,-785.751599238,1195.81045576,-155.671840275,89.5669709957,-49.6545217542,241.016977816,240.21080088,302.312055868,406.395088411,-636.001699905,195.842933665,-270.99196294,65.093739026,-41.5435212158,52.7558836225,57.2991264519,-11.6591265875,150.135935043,-22.4003209178,-176.277202526,-84.9629946814,19.2826023026,-84.5794962142,229.124442825,57.424512432,22.941534142,-12.1515744158,-1.01138685809,37.526663663,1.97191080348,-3.69441962918,-53.4928832309,-78.3502411324,-14.3542559319,16.8068740752,-18.6868445294,42.5879623437,65.9077881362,8.11206205513,-2.20740697656,2.53342360887,2.33902661873,-4.07017624184,7.52615618584,-12.7844115522,-1.69167507691,-15.2046439425,-2.98069415463,23.9080994192,11.9416039667,-7.31228852284,-22.9917457731,-2.3451926665,-0.542166634913,1.22717068535,-0.23620670662,-3.87663395315,0.649693022529,3.11889061273,-2.21952191077,1.03773021494,-2.99633775815,1.27846081574,1.25051514156,-1.08851569484,5.04194934184,1.56725603333,-2.87387315534,-2.70016571253,-10.6452331467,0.274709732454,-0.190617455374,0.585370696432,-0.246690771633,0.164142775015,-0.37997899604,-0.0815819529098,0.518420006667,-0.051316337371,1.15179953859,-0.597506436022,-1.21102387113,0.0147676886061,1.04859544836,0.954949782295,-0.825855697185,-0.654836199122,1.21628306758,-1.9043436781,0.102681581418,0.0872584679381,-0.0562799591508,0.00598916328933,0.16204859255,-0.0702786919425,0.055953207483,0.166784082797,0.124030188875,0.125447090866,-0.0625089679333,0.277866270263,-0.163771735314,-0.230796996227,-0.242207518668,0.204871631773,0.611210425602,-0.424043858313,-0.442392511231,0.0559355676088,0.248668870262],[-33541.6160185,-2110.1238756,1584.79116666,-1154.06060189,2788.45950556,2125.92277017,-1653.59334555,-1442.80452183,394.068746769,-676.973319911,-793.63954406,1141.25658818,-146.330998282,59.8424725224,-64.6658494174,254.509681248,261.997356644,261.939419144,404.447182224,-666.262384094,213.642841969,-254.767928081,107.440788985,-31.1213081961,55.8599719632,70.8671852704,-13.4693847591,146.991583595,-22.275004767,-194.457105031,-59.8808596979,29.6858203928,-74.7913510428,260.268376807,57.3839289778,26.9358653027,-11.4662208059,-3.38650814505,43.3127956626,2.22741419122,-11.8664552435,-50.7390194849,-77.9269005663,-6.47764954433,15.7318777803,-16.1819829759,45.655072641,69.0949315758,8.21802929568,-1.14524772047,2.04609703454,2.1929559661,-4.53202349997,7.82877253952,-12.4518167392,-2.73098562888,-15.9589839675,-1.50124777401,26.3778830237,10.477422072,-6.435243566,-24.897971597,0.808469841203,-0.503531198884,1.43657435123,-0.166587916773,-3.41117025916,0.421806121619,3.20177645049,-2.13809465194,0.78630521477,-2.93730807646,0.905359264977,1.17759949345,-1.488925407,5.4371137119,1.29172158972,-2.07081847008,-3.3557761165,-10.7155981292,0.183483561173,-0.129203672814,0.572011508958,-0.129506962257,0.169861272797,-0.254050577639,-0.174547571486,0.385392730947,0.0182977731618,0.93204062446,-0.632500107941,-1.30310507653,0.109295249771,1.05045326284,0.916541967131,-1.0019152438,-0.608486096049,1.21947785515,-1.92374074584,0.0655083685953,0.076308623269,-0.0433328462036,0.021888298333,0.150225958279,-0.0220456700564,0.0601122967695,0.139956584849,0.114515115108,0.0690598711522,-0.0879786982003,0.226572337558,-0.140557603146,-0.194297067891,-0.20735117538,0.180596776643,0.622241877115,-0.434528990212,-0.527247040866,0.0922145642971,0.243075648207],[-33764.3065351,-2025.61214699,1736.4478671,-995.374281786,2697.9872901,2111.84143256,-1688.45233504,-1566.31941129,480.241986371,-669.722556786,-797.767373075,1071.71542711,-142.610621582,25.027060473,-82.433351573,267.173990499,284.571963524,221.840258032,399.38855913,-695.498178113,230.480725503,-240.643787697,146.637838664,-25.7158289952,59.5000378872,85.3771347548,-15.5883811424,145.307281422,-21.5920710788,-212.127731419,-34.7533210249,39.0585453559,-65.0473612446,288.336699156,53.8913446561,30.7980273663,-10.4149009604,-5.70865312258,48.7168559255,2.87726916245,-21.1215401898,-48.386508334,-76.8011682602,2.48383602819,13.2775250608,-14.0333567296,48.1501931623,71.114349794,8.26105085772,-0.0647993017763,1.52404089387,1.84357561685,-4.94500164132,8.05717484466,-11.814413931,-3.99368045047,-16.6329335736,0.394693435943,28.6015571221,8.43057493434,-5.56763321776,-26.6601147142,4.51752048011,-0.411118960053,1.63012338529,-0.098436114916,-2.90126271084,0.175147648962,3.24137101315,-2.00616636777,0.519381143154,-2.761423448,0.536490561891,1.0748902107,-1.84577534095,5.67946238114,0.940790749851,-1.11755091425,-4.05945725488,-10.5956532537,0.0875416205216,-0.0569937627634,0.551439263368,-0.0110731405626,0.170914628628,-0.11797395364,-0.246841021097,0.224650106497,0.0935538898258,0.688635028166,-0.622143815546,-1.35174570634,0.190589839965,1.03566224016,0.803713225584,-1.1793992562,-0.549494642718,1.1823928617,-1.90188491659,0.0263295463552,0.0643327487508,-0.0315749295646,0.0373660799626,0.133211977748,0.02528757332,0.0670269049189,0.111099526352,0.104737517991,0.00548619580558,-0.104732068242,0.169239325815,-0.108141467682,-0.145617369593,-0.16853856761,0.151244354416,0.612484502351,-0.434866050405,-0.617375646738,0.135458985697,0.231495397996],[-34002.1168778,-2034.1920569,1946.79035183,-809.476384448,2565.35478283,2092.36899512,-1754.24684229,-1717.93125041,568.632685024,-659.230347831,-797.739995095,987.00120032,-146.025959088,-15.2036959223,-101.083281253,279.105637225,308.997170993,183.750796635,391.461588842,-723.386215937,244.950197114,-229.888028015,180.051188641,-26.6562699223,63.7113361323,100.920692677,-17.8836228894,145.887796323,-20.6028796995,-228.829071118,-10.6767883189,46.7023129932,-55.83178611,311.997844946,46.4651318593,34.3529086391,-8.91947334677,-7.85621597024,53.5762553883,3.9742323056,-31.4776348044,-46.8214355747,-74.9025010049,12.4021102928,9.20103652694,-12.2509790385,49.9010823488,71.8122879967,8.20339999575,1.00159738281,0.983174526587,1.25431303424,-5.25979055144,8.19168781468,-10.8519110514,-5.52114352672,-17.2619531,2.79005498151,30.4689640688,5.74302338855,-4.68099203238,-28.1981201312,8.83141151553,-0.265966028148,1.79519648281,-0.0330056734487,-2.35379206869,-0.0753548470159,3.23096383049,-1.81626607942,0.242246849399,-2.46088777983,0.196375812257,0.928622563355,-2.12651530989,5.74010191222,0.509889596107,0.00933237314595,-4.80164128314,-10.2362464903,-0.0152113116329,0.0256110603571,0.521207736604,0.106085823124,0.16890633937,0.0290221386629,-0.285968620495,0.0339190781727,0.17232300036,0.425337969687,-0.561224988842,-1.34015910106,0.253059278909,1.0021268102,0.604457947455,-1.35360180518,-0.472732036809,1.09689484484,-1.82754467332,-0.0146443865156,0.0504319488242,-0.0223209704838,0.0520077367916,0.110381016932,0.0707223827293,0.0788541920123,0.0807727916226,0.0958901978165,-0.0653631552508,-0.111448388742,0.107185743805,-0.0666817124386,-0.0824336527452,-0.125732822392,0.11679461926,0.578420780535,-0.421848725414,-0.710375328424,0.186730324822,0.213130816347],[-34242.5542771,-2181.15150045,2178.05940433,-599.041799861,2392.09804522,2057.88324516,-1849.91824421,-1892.29313496,655.69348931,-643.087535947,-793.43201508,891.45744121,-158.604171929,-58.0487971684,-118.930378448,290.327134536,336.181880304,150.209616066,381.484313075,-749.784849567,256.534160472,-224.262625257,205.137555632,-35.3313128253,68.6211448793,117.412492173,-20.1489976776,149.705554539,-19.7000722801,-243.729014,11.0399513287,52.0902893833,-47.7182899418,329.887319344,34.5653743236,37.4249541331,-6.92132577491,-9.67094802951,57.6519101754,5.57547484541,-42.9012882665,-46.5080050023,-72.0672256716,23.0885183131,3.32740890756,-10.835076564,50.7250196758,71.0414633055,8.00764916677,2.01830357943,0.443124480347,0.378453595232,-5.41417459138,8.19950452534,-9.54561537,-7.34603022689,-17.893970404,5.80208419521,31.8587951282,2.37306976359,-3.73545768331,-29.4075104709,13.7960641268,-0.0714502029394,1.92164201753,0.0277328052278,-1.78043902892,-0.309950898942,3.15895324588,-1.56350132107,-0.0384223852551,-2.02770336171,-0.0802577948468,0.726881187932,-2.28582312146,5.59054673511,0.00141205695464,1.33567514511,-5.56905603781,-9.58359875305,-0.12768198479,0.118876661249,0.47846138336,0.219216274256,0.166072302925,0.186468590713,-0.27734343562,-0.190340954902,0.251978381861,0.148107096604,-0.443789432555,-1.2469286142,0.291144347645,0.949612851008,0.306949261189,-1.51826594599,-0.372247967308,0.954521534501,-1.68777028239,-0.057328033219,0.0334952601566,-0.0172782695657,0.0654850579461,0.0811538302238,0.113043003394,0.0981661684598,0.0493946913038,0.0895173041259,-0.143495733485,-0.106658310481,0.0425442234502,-0.0164516788214,-0.001803371215,-0.0786997879234,0.0777551854215,0.516555228075,-0.391651365456,-0.802900826943,0.247190758904,0.187143103595],[-34472.1329739,-2491.83335255,2405.67438376,-376.554944961,2191.14799975,2005.78092545,-1967.29489791,-2063.48944275,734.029554648,-618.034647113,-783.70682446,793.283683838,-177.554907413,-100.227407698,-131.522524935,300.394708657,366.830305509,124.619991659,370.706671304,-773.651549675,264.539767072,-224.839471533,218.550303045,-52.8490680311,74.3565048177,134.460480882,-22.200488458,157.963112382,-19.3404034457,-255.858228453,29.2366712249,54.4744519896,-41.2275476899,340.407416705,17.5953280745,39.8206543518,-4.43637197914,-10.9911316666,60.6323692636,7.71090363322,-55.3287718798,-47.9246360251,-68.1465051939,34.3404816085,-4.54507604094,-9.76790298094,50.3727746728,68.6467095972,7.64030787131,2.92957867011,-0.0802572006164,-0.841767414924,-5.35347239804,8.03970535557,-7.87373751289,-9.51297782519,-18.5757738247,9.54904070599,32.643445664,-1.73209801549,-2.68566375288,-30.1681600945,19.4434858791,0.169574077735,2.00012414061,0.0803218155251,-1.20138991005,-0.509665556971,3.01232257346,-1.25034188599,-0.315133558838,-1.45050504337,-0.256233443502,0.462803123158,-2.27574004434,5.20170102195,-0.581246132696,2.88502173397,-6.34638824281,-8.58268778011,-0.252446112144,0.224315164575,0.420249921238,0.324249192363,0.164266754276,0.353243811932,-0.206017742941,-0.452100869422,0.329458250631,-0.135592735465,-0.262387249021,-1.0487904023,0.299410874769,0.876931870534,-0.101844862277,-1.66686039617,-0.243057687346,0.746345514372,-1.46857298601,-0.101547347048,0.0126046015448,-0.0184650202536,0.0773936451674,0.0450522811027,0.150763649201,0.12743768981,0.0176522438149,0.0873662160949,-0.228653579956,-0.0885928725115,-0.0221879074993,0.0422815064834,0.0988920389062,-0.0274123389564,0.0345850324981,0.422768167391,-0.340048434024,-0.891035762334,0.318079637988,0.152457556722],[-34679.3784784,-2917.50459331,2621.38526939,-175.852628379,1998.09096431,1941.58656286,-2080.05905553,-2177.68526503,788.254281593,-580.672979526,-766.966730561,707.986933766,-193.849834218,-135.887160847,-130.103918654,307.663190882,400.534172693,111.050873436,361.135237802,-792.993027344,268.909922886,-231.527809234,216.379112642,-79.5429051866,81.0433873735,151.010158519,-23.9717542683,172.029830352,-20.1555032249,-263.930768875,42.9894416249,53.0208788644,-36.6554998266,341.743409079,-4.99594151708,41.3690106996,-1.61403705714,-11.6696969241,62.066892922,10.3440961482,-68.6530599444,-51.5777137508,-62.956061742,45.9776803786,-14.6196314972,-8.96146336827,48.5192329815,64.4816979683,7.0893567035,3.66038776876,-0.575173304391,-2.48891070582,-5.04116072979,7.65409484121,-5.82044397089,-12.0707239167,-19.3505097161,14.1579544166,32.7041405515,-6.63507047966,-1.47006712782,-30.3441489372,25.792342554,0.457884794241,2.02698266626,0.121022319283,-0.647533470717,-0.656844815019,2.77264476751,-0.891638461792,-0.579394580076,-0.716733815298,-0.289862265011,0.137587205274,-2.04441604973,4.54783999623,-1.23345514775,4.68039226215,-7.11663946896,-7.17788579582,-0.391733645258,0.346114832719,0.344099073003,0.416347619907,0.165292712313,0.526670784892,-0.0572830862371,-0.756449999256,0.399982092649,-0.416179391658,-0.00846947103645,-0.720075599298,0.273400313012,0.781917600635,-0.634838849032,-1.79297245907,-0.0808699442707,0.463023365828,-1.15492778596,-0.147238148442,-0.0128288159321,-0.0281592737924,0.0875342904568,0.00192883755535,0.182076992696,0.169056875933,-0.0136707091859,0.0910982476497,-0.32024098185,-0.0555124578688,-0.0839143444971,0.109236471032,0.221917417721,0.0282188886886,-0.0124384447183,0.292585575183,-0.262532520719,-0.970146258799,0.400704929826,0.107746426275],[-34858.7740954,-3265.80798403,2823.85454579,-65.8573121594,1885.6469411,1876.10971146,-2128.95266754,-2150.74475612,789.845855361,-528.043403107,-742.516942697,663.145314134,-192.533443418,-153.007695455,-100.709610962,308.271782282,434.696121886,113.883753886,356.175155257,-805.203792009,271.721664232,-242.887755826,194.803243808,-114.497345236,88.770053912,164.92490274,-25.6155270299,193.399387375,-23.1123141804,-265.971685831,51.6065993518,47.1371470868,-33.892226894,331.934936413,-33.5799133029,41.9693153321,1.19011834792,-11.5890567299,61.289299372,13.333652931,-82.6784723682,-58.033757734,-56.1653011206,57.8836136485,-27.0439895479,-8.19479052342,44.7716746632,58.430139246,6.38667087769,4.11641997213,-1.03316674816,-4.68954250676,-4.46570116075,6.95764679056,-3.38724452141,-15.0500669498,-20.2536464278,19.7839245945,31.9491350991,-12.3969865382,0.0025160188135,-29.7811888849,32.8513808402,0.802195080855,2.00942975252,0.147025749216,-0.163628917373,-0.734189810724,2.40961414902,-0.518836460761,-0.820200514658,0.184866337449,-0.129625200109,-0.236126264614,-1.53139062446,3.61147846369,-1.94708235046,6.7476047377,-7.86091398934,-5.31282042815,-0.547306584007,0.492653878956,0.248580613958,0.490459639831,0.171504175701,0.700641847931,0.183044024738,-1.11061756032,0.455495395702,-0.680764407019,0.327107868639,-0.231150745775,0.210609638068,0.662464362943,-1.30276690797,-1.89022840622,0.118743704581,0.0949415795486,-0.730708446564,-0.19466506078,-0.0429228610381,-0.0488263509133,0.0962566074819,-0.04782179126,0.204615736774,0.225402273154,-0.0441084215562,0.101888311987,-0.41723170644,-0.00611501079006,-0.138455784887,0.184083602555,0.369531835717,0.0888281660358,-0.0631614567957,0.121721652551,-0.154400304841,-1.0346325432,0.496434178797,0.0514862760349],[-35011.2358435,-3342.47982974,3017.21825367,-81.1714597498,1910.685897,1821.13366221,-2073.7155609,-1940.20102595,728.533291158,-461.726596907,-712.052202926,676.499848718,-161.519403485,-145.609472147,-36.5440114722,300.320129366,466.558408091,131.616734542,357.764618842,-809.000223912,274.294484336,-255.005804443,153.60555243,-153.938745811,96.730151701,175.130490817,-27.4984849113,222.313243449,-28.7242125016,-260.721390809,55.0879799012,37.241358777,-32.2370359789,310.887679629,-66.4193597572,41.8032009394,3.6329893922,-10.8207360148,58.193415926,16.5789875125,-96.8327681864,-66.963615359,-47.834044642,69.6626462213,-40.9837677098,-6.87073880881,38.9198407711,50.8846766068,5.70738062511,4.21888587336,-1.49294923135,-7.4413834648,-3.65831375685,5.95997040958,-0.520373803039,-18.3975621207,-21.1826701477,26.1977252627,30.3332855046,-18.7640717523,1.945152935,-28.4170914123,40.3057845424,1.23849706742,1.93870483373,0.169611259222,0.240161200357,-0.778631118492,1.90005649287,-0.140178652852,-1.03496315674,1.22667572822,0.198725488844,-0.600762835804,-0.789351655344,2.42840958849,-2.67413295361,9.07869030759,-8.50559415521,-3.12230554024,-0.718863486751,0.673710117469,0.131276097059,0.5361004927,0.17600933351,0.879961859071,0.518359587012,-1.52107161256,0.487155479196,-0.92269746919,0.736993000404,0.411120524418,0.126706594404,0.527459501254,-2.09783435467,-1.95820769883,0.344073038301,-0.341788938928,-0.197511748923,-0.244242840335,-0.0763794710151,-0.0812299239188,0.102874711555,-0.104103765462,0.212593804112,0.292710620328,-0.0709397975253,0.121107419114,-0.522327518698,0.0589050881306,-0.181649389282,0.267036312628,0.541840836187,0.157101685033,-0.112516142878,-0.0872092758328,-0.0161652818599,-1.08568844237,0.603334205387,-0.0137505111089],[-35139.0481845,-3432.42874875,3176.22175587,-44.7308398611,1961.14642211,1759.68431828,-2032.22475145,-1717.60508579,689.630630876,-395.404323664,-682.996148114,700.20681702,-120.731718301,-145.412815261,32.776339339,295.482273606,500.060299327,145.645830707,359.316306849,-809.811169884,269.554661747,-263.234709373,103.475557577,-190.000536316,101.834579671,187.312032105,-29.7962249712,254.812962864,-35.0095864556,-251.166899886,54.5561666285,26.2583810599,-31.3215628518,284.829947024,-96.2815678981,41.6176667469,6.11855212672,-9.81102089376,54.9769661735,20.4626771801,-109.744601578,-75.2787196944,-39.5746171776,79.7949043359,-52.8064540871,-4.00350164286,31.6483254853,43.6376838209,5.48530398214,3.99814826969,-2.10312647812,-10.2247611603,-2.67187505406,5.04026756791,3.03830178942,-21.8368863021,-21.6782906736,32.0159080405,27.8567918726,-24.5272792854,4.74303460378,-26.4788882697,46.9241340544,1.84895622882,1.72806982042,0.233728367293,0.692482068302,-0.974615486187,1.27938792704,0.360209833029,-1.24254525785,2.27273204095,0.432398968762,-0.801864854182,-0.212887513986,1.16129732765,-3.24575857221,11.5348829546,-8.82196440829,-1.30094943582,-0.90186661823,0.888921934627,-0.0164867877979,0.528291505313,0.143414111311,1.1092121103,0.924501401862,-1.98400801007,0.495688116661,-1.15905577509,1.16677521298,1.08683874931,0.0836931781114,0.421677452316,-2.96537682549,-2.01193453368,0.53460177478,-0.754166292086,0.386488608202,-0.296025633409,-0.109240245308,-0.12052200519,0.101428155584,-0.169350598813,0.191777262733,0.349569855679,-0.0841435422393,0.152585281758,-0.649649545845,0.135224639637,-0.21143532662,0.360032575974,0.734392431088,0.239903886524,-0.140136853001,-0.312105762749,0.135343432659,-1.14665732068,0.709814650174,-0.0730738080707],[-35245.5613977,-3547.53250992,3342.87444189,42.6906844758,2039.81498207,1672.91580025,-2008.58558591,-1450.39987372,673.042421688,-329.875941199,-660.401028376,737.384464444,-71.5448064685,-161.905434781,123.743233955,294.155522524,533.926803791,155.941206849,362.081292336,-808.318789159,256.757606565,-269.21201781,45.7844910299,-218.201907945,103.335302834,202.061086234,-32.7621273371,289.493895739,-41.115083301,-237.491095518,50.3963345154,14.4183006781,-32.6178829829,255.14650669,-120.7632743,41.3198451291,8.62010357452,-8.44527981937,51.7116373934,24.9922680511,-121.354829955,-82.5654971916,-31.7084438332,88.0224618711,-61.9621654288,-0.0948085040434,23.526127814,37.2574790717,5.78025093838,3.38398954321,-2.86384885194,-13.002195553,-1.49639972917,4.26180989477,7.2780462592,-25.2688829595,-21.6585855412,37.0781870446,24.6220774867,-29.418141651,8.18105607401,-23.8097501729,52.507759868,2.63723531532,1.36457885744,0.321191711723,1.17532309645,-1.33721993011,0.543163746604,1.00171129241,-1.40789784644,3.30083682031,0.573791275773,-0.781245248664,0.15071100268,-0.1401714573,-3.59921622292,14.009813827,-8.75458209658,0.0522613749312,-1.09352566999,1.13556058323,-0.197919583545,0.464730148933,0.0628618892607,1.38302883818,1.4062906291,-2.4938772414,0.478080296561,-1.37506355175,1.61943150474,1.79005365294,0.0935269748142,0.355365080932,-3.89158318761,-2.05343249717,0.678443881351,-1.12701994996,1.01057456133,-0.350275384806,-0.140695991143,-0.165313068058,0.0886975238512,-0.244747477927,0.138179170168,0.391549237334,-0.0821017918058,0.196461547546,-0.798403192614,0.223798989303,-0.223374666466,0.462432616943,0.949779056562,0.338604864646,-0.143579653823,-0.54861410359,0.293636484423,-1.21651848192,0.81447789483,-0.12501365662],[-35330.2474562,-3630.20163313,3455.06578858,168.515489966,2145.6630869,1572.03473871,-1983.69383773,-1158.30472302,675.23129724,-268.075546289,-649.940356183,790.604643845,-6.76481142153,-196.132929764,243.524728369,297.36385592,564.762310246,160.962064099,367.202678653,-806.06411963,235.204019215,-271.44772706,-16.3858391788,-233.256471011,100.953914862,219.754357196,-36.6675841493,323.848684476,-46.3316517463,-219.320985376,42.7889165278,1.34540153568,-36.7508956932,223.325385857,-137.103710811,40.9714680141,11.1800407936,-6.53543251263,48.4183890542,30.0865278658,-131.887920482,-88.4328699552,-24.2260356781,94.2548010802,-68.2390815953,4.26782346171,15.442739334,32.3471814956,6.67661765784,2.36055464023,-3.76634883143,-15.7047335562,-0.146945000437,3.66716484984,12.1518103972,-28.632429258,-21.0905843283,41.3089836277,20.8368648601,-33.2365487787,11.9119240523,-20.1005834256,56.9168131337,3.59538983948,0.859291114611,0.410625109534,1.66873069352,-1.8775120163,-0.302965374486,1.78730163078,-1.50157401142,4.2859020423,0.631535077027,-0.498288447344,0.284258824731,-1.38609890227,-3.68605822528,16.3430638801,-8.24501943628,0.88302915218,-1.29452313523,1.41114660868,-0.415408685704,0.348887350303,-0.0742696359983,1.689298677,1.96548763884,-3.04032029536,0.426948497759,-1.55519595903,2.09954627577,2.5143660205,0.163342404912,0.339944537318,-4.84883478577,-2.08742630654,0.755847324429,-1.45293610004,1.66062938659,-0.408342507091,-0.170903859959,-0.213807471168,0.0622006031392,-0.330729971284,0.0489490395146,0.414903328009,-0.0651375014277,0.251137074861,-0.965897212861,0.324462931089,-0.213335188774,0.573458770451,1.18883625365,0.451833109519,-0.121214390832,-0.790446439575,0.450807578644,-1.29328120427,0.917015718864,-0.171196583127],[-35390.0552288,-3583.90914403,3582.59068487,304.483607416,2265.15480118,1463.49723813,-1929.07791847,-871.406815645,689.484591543,-220.721611805,-656.300372614,862.396907442,60.3342142141,-241.846828193,377.530222113,305.240580692,588.776950897,157.331926988,371.517906761,-803.179768771,208.527389855,-273.167617425,-76.3704512217,-234.075910642,95.0244934253,239.996578917,-42.2534764539,355.149591043,-49.9485501001,-197.551869073,32.6673663958,-12.3008612561,-43.1929231648,190.680483536,-142.792881897,40.9882808917,13.8048790295,-3.7010925065,45.0562003339,35.3623009358,-141.800386528,-92.4299727778,-17.4039113991,98.5059427725,-71.576752757,8.98615798457,8.12798341074,29.6849644102,8.28048605155,1.03173478085,-4.75046950108,-18.2972660375,1.35443945226,3.30628165832,17.52399998,-31.9431039492,-20.0017720593,44.6380034693,16.7041661759,-35.8525750316,15.627697899,-15.1259243817,60.0652179755,4.70081784443,0.255464071579,0.472017709398,2.16622964628,-2.58811360196,-1.25782508943,2.69846152693,-1.50026894691,5.19643377256,0.626764202927,0.0728300919114,0.205407832245,-2.46801095154,-3.47654634512,18.3347054613,-7.26357255412,1.17028332243,-1.50935114867,1.71469501945,-0.67057157904,0.191870484277,-0.273527241944,2.01592282017,2.60138401647,-3.612918584,0.331075244951,-1.69053552648,2.61328956845,3.25709686303,0.298689000938,0.387615464002,-5.79486200161,-2.11282333094,0.737231127567,-1.73247901063,2.32044101367,-0.473358441113,-0.200605914979,-0.2636603591,0.0206396265898,-0.426664744942,-0.0773949990644,0.416705552843,-0.0329484864692,0.312897275424,-1.15006294662,0.436547820516,-0.180322601577,0.691259509943,1.45229170585,0.577134354844,-0.073390923672,-1.02922469781,0.600163355881,-1.374319692,1.01896767809,-0.214676962394],[-35418.5156937,-3492.96870961,3775.91223527,426.779288653,2378.51899999,1345.52795672,-1858.10522227,-641.398153915,709.595645413,-193.403166129,-684.320283934,945.820772759,103.816976663,-288.501073657,508.149737723,316.814806599,604.093724316,141.095780441,370.861409603,-799.132278868,177.920080811,-279.907482404,-125.43370375,-219.954044955,85.8662332847,261.890537829,-50.1824346069,381.344592331,-51.7008518993,-173.980400934,21.0058436898,-26.2779779981,-50.484168369,158.358130434,-136.994897049,41.7796699741,16.4242751222,0.416090429683,41.5377824239,40.3547360978,-151.497644802,-94.2852912825,-11.7414867415,100.619923513,-72.0666733102,14.2615910114,2.17951998719,29.6215634964,10.6716997813,-0.497271376595,-5.74690455168,-20.7458584422,2.98279056411,3.21437143521,23.225416503,-35.3150371466,-18.4782116932,46.9797117315,12.3611844185,-37.163815786,19.0876470518,-8.81980426005,61.7756477991,5.92752143042,-0.405350132477,0.47899757423,2.66367170404,-3.45060452685,-2.31565025942,3.70974436011,-1.39851439169,6.0114824114,0.560415963839,0.960263364612,-0.0498604303267,-3.28867971744,-2.96759729756,19.7914081604,-5.82094157148,0.909448270509,-1.74119620728,2.04434770493,-0.964217839868,0.00354077399365,-0.536592670014,2.35352975794,3.31147434171,-4.19703971295,0.179347558592,-1.77831951832,3.17506437251,4.01163569355,0.507968867558,0.50957109507,-6.68122014177,-2.12602751645,0.600076690679,-1.97434681586,2.97843845,-0.547927632772,-0.230611298279,-0.312281243874,-0.0371299577672,-0.531380464849,-0.241816982452,0.394914437049,0.0169316573228,0.376353009773,-1.34850754188,0.560185629298,-0.124212558346,0.81533287534,1.73961586351,0.711318340397,-0.00106646873189,-1.25482776071,0.737956981527,-1.45341203052,1.12077967095,-0.256560159308],[-35410.3085264,-3441.26019604,4143.30147665,529.352674191,2457.57474781,1239.79613058,-1753.33290386,-429.306917585,733.538440483,-184.887748535,-732.781284836,1024.75565,121.519009596,-309.62846464,637.305637898,330.22480186,612.477220459,110.890170958,363.735296314,-791.404109535,143.648865944,-288.218007287,-152.821060474,-198.960023414,73.8004904408,284.116917739,-61.0789971003,402.532455555,-51.7292337829,-149.782194814,8.85026845579,-39.6840245211,-54.2857115114,129.73629511,-125.361426833,43.6666917275,18.9389481429,5.88923467788,37.5543041595,44.5465288358,-160.740269924,-94.0423018879,-7.35756650811,100.170447976,-69.8361458413,20.9565253144,-1.31975883786,30.7893353272,13.8626276919,-2.12236105769,-6.70528427085,-23.0551165377,4.70504228495,3.36299695697,29.0386084914,-38.8084238945,-16.6875252861,48.3117991771,7.76886833387,-37.0954418132,22.1403791215,-1.35114037875,61.6431298894,7.24707225769,-1.10154944155,0.410398916925,3.16898908323,-4.44342111033,-3.48662711478,4.80141399961,-1.21518612257,6.72536747157,0.405595131495,2.16917879745,-0.433900877753,-3.82304588647,-2.16778821603,20.5984943062,-4.04547370315,0.10237179818,-1.98916695273,2.39549338944,-1.29447945313,-0.211671374108,-0.865014136237,2.69739727359,4.09317117503,-4.77927254223,-0.0389056130914,-1.82152809505,3.81490806058,4.7489737995,0.798502972225,0.711844033096,-7.4687349318,-2.11762674507,0.347423502793,-2.21720075836,3.62795439424,-0.63418320231,-0.261101997391,-0.35626545359,-0.113105110268,-0.642970411837,-0.444705182124,0.347297270888,0.0879303010768,0.435245327523,-1.55673397973,0.696193868698,-0.045024052779,0.950941173335,2.04480202892,0.849043435642,0.0928781663178,-1.45720955898,0.868497504376,-1.51996487876,1.21727708146,-0.295608805562],[-35361.5005612,-3341.57886842,4419.49259513,609.415955393,2464.4464176,1148.85752598,-1614.31993819,-233.208141506,760.643074469,-196.466467934,-789.864677172,1083.80556741,132.318287295,-312.912079363,761.880277853,344.316589743,616.066189279,69.4301223181,350.562914649,-776.945101956,108.625514594,-291.82171565,-162.731077354,-182.81410982,59.5180047387,305.233181482,-75.4094290321,419.876695636,-51.0839950018,-127.020773534,-2.3582760272,-50.4887029819,-52.3410073165,107.185117228,-114.78332748,46.732064005,21.3463720123,12.5398084524,32.6717095115,47.6868853128,-169.151440152,-92.248005518,-4.5060718906,97.3036043405,-64.6836755563,29.6303580339,-1.27996359696,30.9665485015,17.8280485568,-3.7358207831,-7.56250459695,-25.2753609356,6.55433376319,3.74402113542,34.7300264629,-42.4213687895,-14.8938852733,48.5212004882,2.99532487915,-35.5402668241,24.6791472132,7.04338821994,59.365511176,8.63930696756,-1.81328878228,0.245715121007,3.69506338105,-5.5447007926,-4.78689000017,5.98717939669,-0.960137446189,7.29075997572,0.110038953561,3.67364419499,-0.91786376806,-4.09522976869,-1.06797924354,20.7299720369,-2.15237438842,-1.20135392356,-2.25267191416,2.76165849608,-1.65692827531,-0.450811348185,-1.261118751,3.04830293404,4.94057566158,-5.34923406433,-0.324402042176,-1.82567329588,4.55411010694,5.42268877385,1.18347780261,0.995160477798,-8.1342688671,-2.0834677155,-0.0109307953729,-2.50249289303,4.26306368366,-0.734103360398,-0.292828443224,-0.391434744638,-0.208459666992,-0.758952354996,-0.685672393324,0.272405399383,0.183672356232,0.482036996292,-1.76742618865,0.848104080942,0.0542677780819,1.10325162334,2.35995344961,0.986415421191,0.20218471436,-1.62903337243,0.998442515475,-1.56222600886,1.30121610837,-0.330167956766],[-35266.6478156,-3255.49528604,4537.82134865,640.132088497,2410.82368526,1043.03311037,-1497.05878114,-29.1817157643,791.429436457,-236.275479696,-843.621008437,1119.12663687,145.079465242,-317.642620754,880.008049207,359.983536409,617.046161502,23.4224417819,329.84606587,-752.808680232,78.3369546925,-289.701256418,-164.808724329,-176.069986735,43.4653872678,324.344287776,-93.3875422678,434.221040536,-49.9821697228,-107.710054578,-11.6532840296,-56.8897030796,-45.8117438044,91.7538338967,-107.770161312,50.9209507794,23.5640088277,19.9254201472,26.6315244109,49.7688929757,-176.395717938,-89.3645804582,-3.18812360908,92.1881153394,-56.6717359515,39.9650762603,2.02843969409,29.4381841833,22.5355840346,-5.24066018856,-8.22957695995,-27.433735647,8.53114627446,4.31460295784,40.1480200357,-46.0973649652,-13.4139469912,47.4882618706,-1.81880447009,-32.5696763588,26.5495586177,15.7826245102,54.8966197931,10.0723475376,-2.50873688288,-0.0244917767546,4.24249107172,-6.72704746744,-6.21928253079,7.28290351479,-0.682111393298,7.6474284347,-0.341114029397,5.40307135257,-1.48215283281,-4.17093301494,0.34710860164,20.1704317686,-0.435869686429,-2.90351077374,-2.52950076028,3.13338822443,-2.04694782887,-0.710380392762,-1.71944876383,3.40595019814,5.83762182287,-5.89092598849,-0.667356323572,-1.80589311656,5.39672344082,6.00034590852,1.67063443626,1.3549650431,-8.67775425092,-2.01460964454,-0.454832581722,-2.85662748208,4.87876625231,-0.848236951239,-0.326698177497,-0.413216468338,-0.322597696078,-0.875864237247,-0.9639369729,0.171426207256,0.308905340649,0.507918099329,-1.97108878286,1.02276070632,0.169603158904,1.27294025861,2.67772661146,1.1221603867,0.319922540562,-1.77018511841,1.13228677796,-1.56406646196,1.37125138718,-0.349229902502],[-35119.5687622,-3171.94560942,4670.91151162,617.069036989,2341.01966679,939.383042667,-1381.00658006,215.468365184,826.218779653,-304.555438143,-884.117566228,1143.02472229,165.019179548,-314.091165596,981.13155164,378.798492651,616.411467591,-20.3315259683,304.580321073,-718.833857895,58.8236473377,-284.573547999,-164.362292782,-177.876554594,26.4765554456,340.877633511,-114.633734703,445.6890867,-48.2196795674,-91.847321199,-18.8648073177,-59.1585112943,-38.8966086797,81.8900627755,-101.448025468,55.9540324086,25.6838838089,27.4016449175,19.1775655064,51.1929957282,-182.01328462,-85.5229967783,-2.97363924879,84.7972079471,-46.6903745062,50.5266744433,6.52972443172,27.3263165138,27.8890974051,-6.58995347712,-8.63670844945,-29.4714059432,10.5764903141,4.94534160118,45.3284618818,-49.6839030487,-12.4891616308,45.1091389243,-6.55403042523,-28.4249984961,27.4817014616,23.8632085095,48.5175364169,11.506872366,-3.15124778308,-0.384196957129,4.79202778695,-7.9719724179,-7.76086463047,8.7125381082,-0.478025039876,7.7672039182,-0.886719311325,7.26732653206,-2.12402841516,-4.13814873835,2.05276010573,18.915219457,0.768090444201,-4.82694288324,-2.81561036805,3.50250531017,-2.45535226519,-0.985272545999,-2.22138061065,3.76771958592,6.75635742938,-6.38112891712,-1.04521421971,-1.77349763332,6.33425110126,6.46663644948,2.259423808,1.77520521435,-9.11141010574,-1.90621884543,-0.956644281527,-3.29582341623,5.48220282054,-0.976295370118,-0.363561890109,-0.417161425132,-0.451947020915,-0.987894719128,-1.27670305831,0.0478368110701,0.46902566682,0.504312237204,-2.15453192789,1.22796232962,0.299305313497,1.45679705293,2.99166248888,1.2515032254,0.439290947259,-1.88660895347,1.26922254052,-1.50710910237,1.42965059434,-0.330621789246],[-34918.9720709,-3194.00243027,4797.24552972,556.472841404,2294.76048438,879.917414471,-1253.3569331,416.857294512,862.791104766,-391.964686392,-905.790343666,1163.4531494,203.104542652,-282.919856874,1033.42684375,403.171001895,612.892921801,-55.7559158722,282.640067966,-679.055472007,47.5654697559,-274.948686076,-159.86475133,-186.405867229,10.0567061676,354.631768808,-138.087577648,453.900234703,-45.8946862555,-78.3027415309,-24.3073347758,-60.3407138317,-36.1938400626,76.3529049985,-91.4189245686,61.3142040694,28.0961546821,34.0727752182,10.1447936177,52.7314076686,-185.169286632,-80.7377495437,-3.25908249343,75.3151924701,-36.0294285887,59.1403661546,9.60455142934,26.2733767074,33.7327861057,-7.79336229738,-8.78041802977,-31.2206225208,12.5572830495,5.47230942416,50.4036582984,-52.8963399992,-12.3125592154,41.2785277856,-10.958774248,-23.4157525295,27.0971703577,30.2912624318,40.6375878163,12.9047120866,-3.69901597261,-0.79632425451,5.30687917064,-9.28120799284,-9.37183178283,10.300240992,-0.45913557451,7.6197894747,-1.41019409772,9.17511985998,-2.85759017448,-4.05094998247,3.98452936875,16.9632681447,1.17348782403,-6.74913216359,-3.10588279662,3.862774322,-2.86728096447,-1.26789973319,-2.73703125617,4.12590434532,7.65780430916,-6.78664595097,-1.43092989978,-1.7314141705,7.34544153008,6.81929054244,2.9472533657,2.22741243666,-9.43777789756,-1.76644943727,-1.49612814769,-3.82643817698,6.08063223458,-1.11768157578,-0.405047543995,-0.399237473211,-0.591039616675,-1.08654138901,-1.61875996238,-0.0938472245195,0.669902481392,0.46368883752,-2.30047365641,1.46899453428,0.443975195017,1.64904598117,3.29736343329,1.36570428442,0.552054829712,-1.98458331402,1.40160484818,-1.37725917342,1.4764390253,-0.249143215585],[-34666.4984551,-3292.80008453,4995.90218119,464.922116077,2295.61307791,863.989436423,-1092.7048121,575.745177304,900.419654593,-494.988845468,-899.477685336,1179.60045967,248.744350257,-225.62175974,1029.71369754,436.115429648,607.067781027,-74.8706455722,269.16590747,-636.360707405,38.9345248666,-261.942166416,-151.954793593,-199.861193107,-4.34479418482,365.402052263,-162.738669974,459.125063388,-42.1740304683,-67.3810653895,-27.8852499527,-62.6163747565,-40.5553512832,75.9323382474,-75.3227093915,66.4513175954,31.1750607095,38.906487565,-0.483854168283,55.1129146032,-184.498351997,-74.6182155723,-3.80716522177,64.2498705237,-25.5303644195,64.4190532636,9.4829603392,27.3466244989,39.860248457,-8.81674170919,-8.67500623398,-32.468673569,14.324479071,5.80805269582,55.4515086863,-55.3436110207,-12.9399397152,35.8478507048,-14.6272676863,-17.8625666138,25.14407577,34.2947707345,31.5495959125,14.2030217133,-4.11117954534,-1.22864536213,5.7542569513,-10.6554388727,-10.9971766637,12.0632657976,-0.709353591942,7.158847564,-1.76519169755,11.0619057393,-3.67211438523,-3.93171240666,6.0319548763,14.2741703932,0.544572357186,-8.43278246054,-3.39024144878,4.19997084708,-3.26375671996,-1.55026206693,-3.23673282099,4.47077606025,8.49104140042,-7.06041672909,-1.79538989995,-1.67318357407,8.39988429534,7.06633803839,3.73476799103,2.68386066179,-9.64404774995,-1.61132578517,-2.07920559292,-4.45215777043,6.68096855981,-1.27040255104,-0.452220435959,-0.354510154523,-0.733927636374,-1.16147115349,-1.98260159536,-0.250246590855,0.918608940828,0.378358941362,-2.38814213326,1.74939457337,0.605980559628,1.84180343788,3.59328659312,1.45368943578,0.64791884512,-2.06844949875,1.51905755715,-1.16522136219,1.5050532707,-0.0770525312176],[-34363.9035643,-3312.18435967,5167.42707503,349.881268343,2348.50661378,838.397479441,-950.875285503,721.213656946,941.554935208,-618.359833382,-853.576319872,1198.03728637,263.457276637,-187.917037073,1002.76581383,477.378945086,602.752978338,-71.6330716682,262.059612602,-591.719745425,27.5810181001,-258.816137061,-153.167189551,-214.586351421,-15.5728108725,372.053265296,-187.528773248,463.260007894,-36.8009468245,-60.3903942282,-29.0178117655,-65.3931316638,-51.6468776405,78.0198002756,-51.8510429973,70.8547761889,35.0927711918,41.0074254737,-12.6690023039,58.8686154603,-178.51152406,-66.2587833732,-5.14692126462,51.3100911248,-15.5058075462,66.1651080582,6.16563570449,30.6617498428,45.9609280715,-9.59317069563,-8.33412969053,-33.0986211726,15.7879734222,5.95901197618,60.3545180602,-56.7117090662,-14.2649139385,28.7949294537,-17.2717113884,-12.4290120194,21.6255524348,35.5884224506,21.5228299637,15.3270873923,-4.36507995871,-1.65463341053,6.11497978114,-12.0800200588,-12.5973297676,13.9731130081,-1.22037373069,6.32580147888,-1.88187767778,12.9004927272,-4.48227540748,-3.77621476745,7.95081273295,10.8036716983,-1.20447460137,-9.57124809169,-3.65082263904,4.49535145648,-3.62255383163,-1.82458143963,-3.69207358353,4.7895761379,9.20085435654,-7.15645481846,-2.11702807269,-1.57058123945,9.45848545014,7.20859674594,4.61258114823,3.12374628048,-9.71174223795,-1.4803334685,-2.73803963663,-5.15206448841,7.31289172643,-1.43180170423,-0.50399643669,-0.277578497147,-0.874653173716,-1.19957358139,-2.3575054037,-0.417595450281,1.21877657176,0.241535854711,-2.39471897662,2.06881346863,0.787895790892,2.02638604661,3.87703302579,1.50004577592,0.712527411477,-2.13466976842,1.60786259309,-0.868664847319,1.5078366871,0.21086588963],[-34013.6151115,-3234.9471634,5459.92991997,260.401285582,2432.76977855,745.971138945,-828.055231824,891.344747028,964.695877603,-739.61291212,-792.613134437,1233.80940091,253.548533767,-135.029083699,995.27751755,520.160253079,600.051336626,-52.485534424,256.13651254,-546.818836365,12.4997848078,-264.497456649,-155.172756502,-217.874044302,-23.3011244968,374.979960249,-210.769384474,468.533522352,-31.8183206991,-56.0744555103,-25.8784918508,-62.4473348279,-65.6409733146,78.7551801718,-24.8006423334,73.450014317,39.8348847921,40.5807293914,-25.9946206854,64.1571581708,-167.787911333,-55.5302396818,-7.48120917223,35.3066332726,-5.63790888438,65.0313268836,2.09209404759,34.3376758554,51.7356685982,-10.3953301871,-7.93819016825,-33.233386566,16.8221998042,6.30056814325,64.9530046094,-56.9177972459,-16.429918162,20.523107079,-18.8628790948,-7.66758641753,16.4973732717,34.6796964201,11.0462575822,16.2695361868,-4.44415523023,-2.00245974805,6.30646689402,-13.5557094691,-14.1360733821,15.8825629671,-1.85176770485,5.15470121109,-1.79579811112,14.6277859479,-5.23527646312,-3.57290910727,9.47188416708,6.64821397957,-3.92117374325,-9.90852788348,-3.8733049073,4.74989973913,-3.92815033532,-2.08044016377,-4.05761563517,5.04605079815,9.74985268112,-7.06491372539,-2.4079891971,-1.36122692206,10.5220809682,7.2251221832,5.5359971579,3.50214344392,-9.64206550778,-1.41186837699,-3.487843336,-5.87637538399,7.99430951271,-1.59896265031,-0.5566010487,-0.169112807787,-1.00677009526,-1.18834486442,-2.72774315026,-0.587604186592,1.5612322235,0.0527768150918,-2.3042881111,2.4186524708,0.991273069698,2.1945244492,4.13545622315,1.48827236914,0.730778738554,-2.1742493639,1.66632557706,-0.507509376143,1.49869352651,0.618912679886],[-33623.9248901,-3144.08832423,5650.94723727,236.102637222,2509.91596789,583.35043714,-676.338828917,1087.62929911,962.93506361,-842.701320023,-741.110271766,1280.8157483,250.147964198,-55.8368164236,987.527287626,560.107909409,598.711863445,-21.8777642964,258.687327251,-502.374591225,-16.8651886001,-260.485230058,-143.493218055,-209.471479228,-28.9117805306,377.10106236,-230.801793513,474.803442772,-27.2922666109,-53.0187440897,-19.8178251002,-54.9761156648,-79.358406016,78.1947179893,2.16889666357,73.2437114338,45.3225409002,37.9446424983,-39.608303615,70.6506924081,-154.533728627,-43.7219798498,-9.97683624146,16.4439998313,3.48520410912,63.4416205897,-0.595274784337,36.0928418628,56.9961603305,-11.6538673266,-7.72587902822,-33.0166095178,17.145589291,7.38603289643,69.1030015194,-56.1022159298,-19.4721272242,11.5339759837,-19.3387058223,-3.88517257708,10.2373745024,32.3340894909,0.965991337082,17.0294624266,-4.33159046158,-2.17981846812,6.17161049295,-15.0580217837,-15.5839969149,17.5960367775,-2.44378217298,3.7500266776,-1.55992143689,16.2238981607,-5.92892665845,-3.34638507634,10.4066310693,2.10002753255,-7.21225784075,-9.36622891109,-4.04314509146,4.98798952659,-4.17639674139,-2.30244065585,-4.28317417452,5.18275000149,10.1179669781,-6.78719974519,-2.68915398933,-1.00103448324,11.6104795097,7.10385975096,6.43666829606,3.75597207293,-9.40377657436,-1.42725034359,-4.27734194563,-6.54501602755,8.73177585107,-1.76901393086,-0.600785901198,-0.0330244108084,-1.12321524407,-1.12110347361,-3.06949398315,-0.748465195138,1.92451250555,-0.178295680687,-2.10713982908,2.77755740594,1.21844742062,2.33571095633,4.35394763233,1.40928903485,0.701427557782,-2.17780086631,1.69871537366,-0.110358847657,1.51102718938,1.129945906],[-33212.3982773,-3120.27872783,5737.82702334,241.004097881,2595.88659703,425.307724011,-544.899518425,1215.92100422,955.242348872,-930.946147881,-686.911243803,1316.06702636,256.852710509,25.5851512483,963.128996844,597.545838272,598.627300293,20.5401541606,271.991705416,-456.842000035,-57.7387075222,-247.978112707,-122.105169015,-195.178032148,-34.6562190801,378.723354509,-247.442657728,480.787590245,-21.4400120943,-51.7192188004,-12.8821042687,-50.0158466405,-90.0525241559,77.4296145092,27.7576006347,69.8669422261,50.9056130887,33.5073555936,-52.3897009475,77.7481876032,-141.350761764,-32.3156274724,-13.5994582483,-3.06969188173,10.8082784594,62.3883104191,-2.60996492844,34.7814352297,61.4866374937,-13.6345587044,-7.94071327476,-32.5558558993,16.7904145294,9.36776400155,72.2439264359,-54.5023072937,-22.9993065371,2.30705798952,-18.7731050515,-1.62250595851,4.01707830834,29.2887058238,-8.11646090736,17.5695355221,-4.01256431137,-2.1375720866,5.58908645637,-16.4895843866,-16.9749346227,18.9771168092,-2.83740094919,2.24626066493,-1.24244904859,17.7084113389,-6.64210129327,-3.10159181334,10.6824456468,-2.37852587811,-10.6143599525,-7.95654510252,-4.13145791436,5.24895177736,-4.35814183619,-2.46908774407,-4.31280301436,5.14579364409,10.2762445922,-6.33414253235,-2.92118406906,-0.49120037547,12.6809514827,6.84190823579,7.26813595358,3.79073222425,-8.95572435024,-1.5522921985,-5.02440989011,-7.04917487427,9.54474659056,-1.94247872498,-0.617917136978,0.125993224201,-1.21597428845,-0.987233205803,-3.35276855881,-0.886165719343,2.27793083317,-0.434618289049,-1.7992455502,3.11658036557,1.46220383807,2.43571451581,4.50766655128,1.26549929073,0.630013645971,-2.13139747222,1.70556929391,0.308017713305,1.56959800281,1.70363356481],[-32806.5898837,-3069.69673157,5757.45331112,223.368923529,2687.1773451,286.213589756,-385.13221561,1285.69303685,950.238269204,-1011.83940709,-624.455072401,1330.22807699,251.115110782,92.3288219987,943.943871331,630.836231527,595.028490312,68.7483707902,293.787618599,-410.225201822,-103.637442275,-235.575420247,-95.135372282,-179.187494157,-42.501450826,378.425318897,-260.605347589,484.089174741,-13.4523613131,-53.9486069362,-7.65131786984,-50.6620196423,-97.1322310608,79.3174645166,50.2336631348,63.1270802843,56.0840540636,28.2630387944,-63.589476765,84.7653801487,-130.911592037,-22.7702411881,-19.6177416384,-21.140332067,15.3421130375,62.2762018152,-5.98994271594,29.6842377674,64.9034330459,-16.4901917638,-8.80639748185,-31.9263938377,15.9634813155,12.1617051989,73.6573573501,-52.2948129471,-26.6722919803,-6.82354576044,-17.2626938535,-1.14766712554,-1.02618672381,26.2814063948,-16.0468763534,17.8440985106,-3.48526226078,-1.84269587761,4.49168304289,-17.7293737537,-18.3105597904,19.8967714228,-2.88815303862,0.798970060793,-0.921235443959,19.0215490493,-7.50429260522,-2.84376301937,10.2552584,-6.24700603085,-13.5972574943,-5.76111442595,-4.09490832099,5.56632783251,-4.46060777813,-2.55855372535,-4.08225389007,4.8924336557,10.1807041692,-5.71709482711,-3.04215373307,0.146628095393,13.6662725687,6.42337101117,7.96296169885,3.51153650083,-8.26485808269,-1.83169753677,-5.65775698629,-7.29153880566,10.4231668725,-2.11893398718,-0.584605304118,0.301406192339,-1.27766645351,-0.772475316598,-3.54207376516,-0.984469724211,2.58534015979,-0.698793952518,-1.37958045976,3.40802748369,1.71116016468,2.47499196724,4.55984866094,1.05760121981,0.525482703385,-2.01062047419,1.69001003617,0.730093366324,1.68527578936,2.28222906672],[-32450.9568391,-2944.03124675,5750.23266107,161.379237393,2743.29928391,142.767356377,-217.040129912,1291.25989896,965.598642177,-1078.5666122,-557.599651496,1333.56874316,223.004303672,147.054947521,935.839028425,659.784413395,588.235083222,113.675708069,328.463647636,-367.31490319,-146.075827009,-230.463375736,-70.5218225242,-164.202866839,-53.9829168812,375.202758464,-270.705905066,482.060277365,-5.98410298382,-58.7832251122,-7.97914305823,-55.0580065676,-101.067737189,86.2547868152,66.3923515307,53.2439872056,60.4964611151,23.3760517865,-72.9342775617,90.2883116351,-125.417012534,-17.2673617552,-27.9063482282,-36.6004857631,17.1563356681,63.3948380465,-12.6675297108,20.559659344,66.9884331594,-20.3125135286,-10.5445674476,-31.1725966331,14.7286466518,15.5713722226,72.4219709246,-49.4888069764,-30.386957229,-15.3654837318,-15.1266346929,-2.3942909515,-3.91420804132,23.8482881532,-22.5991521278,17.8027410684,-2.74353944298,-1.29348003181,2.83823097303,-18.6711151492,-19.5477860359,20.1953238593,-2.50205926991,-0.440412216752,-0.627801195604,19.9720580654,-8.66558788214,-2.5922420808,9.08216197658,-8.97890883528,-15.5490375506,-2.91153125534,-3.87820834426,5.96539684926,-4.47343425134,-2.54969925175,-3.52815897486,4.36800606734,9.77343361224,-4.94491735971,-2.98799570359,0.885111440135,14.4723702215,5.82035077264,8.42434922781,2.82929213531,-7.29997565242,-2.31504485718,-6.11966215955,-7.1710935656,11.3392209894,-2.29530384903,-0.476154625303,0.485586219423,-1.30282627094,-0.462103499321,-3.59851561211,-1.02517896065,2.80453214675,-0.95508320181,-0.844214485802,3.6199102674,1.95426199399,2.43069733285,4.46416365945,0.781433510317,0.400967818482,-1.78477227053,1.65561946438,1.13096658772,1.86257559864,2.80048943727],[-32215.2530019,-2804.32480827,5797.30149227,54.3298230394,2748.94243587,46.3500038333,-45.7333335597,1356.9048262,1032.60169644,-1127.20435948,-483.575809274,1353.21495289,185.007088482,261.574568373,936.482039037,689.99359947,587.822190213,144.35669248,375.013278411,-330.88055881,-168.592584214,-233.57806964,-44.5108868338,-145.181278785,-68.0479003316,370.776389398,-278.318044009,469.124940503,-7.50244085508,-54.1296964682,-10.834036374,-56.0457677711,-104.154233376,93.9979972163,69.190444393,42.7717134241,64.5952229599,20.4812104796,-80.6610520275,91.7867047857,-126.120049895,-17.4286868645,-35.2354638114,-50.4503585031,19.1599832288,65.8523904968,-21.2476633786,8.71251319351,67.841687677,-24.7005600311,-13.2243337613,-30.0646976755,12.6542145803,19.2822688459,68.1462462893,-46.3060625454,-34.2184822672,-22.7576878651,-12.9579702623,-4.21764244228,-4.32284160525,22.4595733699,-27.0227812891,17.4050576534,-1.73978404962,-0.548979099609,0.776722269631,-19.3929979104,-20.4958857881,19.8517150231,-1.77544526246,-1.38079247985,-0.36892355868,20.1882406727,-10.1971917197,-2.28295739953,7.19893971156,-10.2997301151,-15.7924963033,0.19815143929,-3.42830476959,6.45254954284,-4.41082291128,-2.39377309137,-2.63775248062,3.51757050623,9.00433444679,-4.02853828566,-2.75549765708,1.65970249705,15.0029801816,4.99479465077,8.56150398652,1.73605672796,-6.07462764794,-3.04811463095,-6.40603953991,-6.58956350944,12.2235719193,-2.4711457357,-0.279367691236,0.674839958248,-1.2824013487,-0.0508362800958,-3.48888753798,-0.987679304888,2.89074335839,-1.20242445527,-0.200565893098,3.71527752302,2.17716528198,2.29490166017,4.17143320021,0.433319835308,0.268817531794,-1.43944230708,1.59659968353,1.4695368995,2.10128264744,3.20427849716],[-32148.3062751,-2699.58147005,5826.44731825,-62.6308615531,2791.68532997,-88.8853415391,48.5793679126,1379.04591559,1105.33517554,-1170.36498691,-419.082403273,1402.77452667,132.946177147,362.766826528,886.564809532,729.316222365,594.92899785,160.936092856,419.671115315,-301.202578688,-179.945402549,-231.522534662,-13.6954565493,-116.632652962,-83.3466795863,368.462401197,-283.050146003,441.854459222,-15.6487135979,-37.2774019848,-8.83103945289,-53.3296682969,-108.19657071,101.75588065,61.0465348134,35.2429678986,68.6190262804,20.6748700941,-84.4653969937,89.5010512386,-133.296879211,-21.0651740575,-41.6721319203,-62.1168950389,23.1886231544,68.1982255784,-26.1355957264,-4.40265565133,68.0131914079,-28.7201698512,-16.7896551364,-27.9651380084,9.80542291087,22.8851187414,61.3902595329,-43.4375966193,-37.9609924811,-29.2346169563,-10.5070481479,-5.69749693211,-3.46021933194,22.8764669141,-29.5905453444,16.6949666527,-0.409438746725,0.300778926777,-1.44923446554,-20.0149707312,-20.8154063857,19.0336597893,-0.971503326441,-1.89432619201,-0.135291275782,19.3651853329,-12.0288089848,-1.75969462347,4.89293549573,-10.3811932202,-14.0973021581,2.86744402595,-2.69502187845,7.00023940338,-4.35533421062,-2.03959500779,-1.4393007205,2.28632069492,7.86200266893,-2.97243586379,-2.39680839459,2.37122787183,15.2316238351,3.94296527379,8.35583435268,0.297990111101,-4.68459926527,-3.9919824345,-6.5232213115,-5.52116842084,12.9447843589,-2.64678389673,-0.0048311099482,0.868387240431,-1.21170479433,0.444669654336,-3.21456548643,-0.866038421868,2.82616424478,-1.43814152812,0.509218119058,3.67608547026,2.36437716021,2.08245178116,3.65222402472,0.0157409245832,0.126326830131,-0.988440591477,1.51285072429,1.70265027505,2.41067017044,3.45042254184],[-32117.9365425,-2644.44928829,5905.61728547,-179.469746901,2861.40777728,-303.973038259,222.387242471,1430.91711709,1131.24582237,-1223.6335578,-354.167658101,1437.02344511,86.5360254684,422.190769883,804.058704491,767.20653588,607.132379324,175.697695704,463.375926186,-262.811538233,-207.534344448,-220.787675743,27.3139149414,-102.122900456,-102.174615142,368.367826918,-285.583008655,406.909716815,-18.3931353,-15.429321825,-5.10571473135,-50.3842152227,-112.02675777,115.833302222,47.9211802623,32.3421492916,70.4518240795,23.0295194007,-81.5644007485,84.6535521932,-144.644632151,-24.9975941747,-48.9161371347,-69.5150937292,30.0081075487,69.6183662333,-26.5389533374,-19.5260687832,68.0992018045,-32.28748446,-21.2926157115,-24.6887558715,6.59698112256,26.6613623975,52.9129802607,-41.2074313024,-40.8226425675,-35.4725136842,-7.21384325304,-6.43420603362,-2.69654793736,24.5746461822,-31.9532541141,15.7750789468,1.11555668619,1.12135409715,-3.71788716796,-20.616864374,-20.3316827494,17.9807802589,-0.20703426669,-1.92996939655,0.173685497466,17.6107966072,-14.0348594208,-1.04236118971,2.53855117558,-9.80970159686,-10.9302920663,4.58932378957,-1.66381063604,7.54750521653,-4.4188194843,-1.53941124874,-0.0153615984052,0.745142100142,6.4502550001,-1.78336648904,-1.93592867391,2.98216520875,15.1789981078,2.78057613542,7.90972060615,-1.42652332425,-3.21296554245,-5.04351808347,-6.49995730692,-4.07976566161,13.4181718832,-2.81228444874,0.3094028291,1.06933123453,-1.11818458122,0.984291211537,-2.82384020303,-0.687973737028,2.63255265172,-1.63949495242,1.24003930186,3.51296683265,2.53299763507,1.8303182602,2.93645286671,-0.446569014246,-0.0324302221557,-0.458047426337,1.41806312627,1.83046308465,2.78243831548,3.53057881529],[-31995.6590298,-2532.39676313,5946.45416133,-290.128441265,2888.03719749,-547.591647185,445.212360415,1494.50197025,1102.76302517,-1286.3220865,-317.704902412,1420.02377361,37.0614816072,431.770277063,710.452484533,797.742689521,616.576581619,195.006474262,505.623177781,-218.312966031,-249.885104312,-209.02322216,73.5652496503,-107.380182295,-121.076400459,367.331565258,-286.855057098,372.149454184,-13.1015801119,1.05136543227,-4.58949076894,-48.6692768714,-115.100956189,128.610284993,32.7075642048,33.2979642664,69.5933048961,25.5075607507,-72.2480395645,78.6424326678,-158.522207249,-28.9427086669,-57.1423046637,-71.6586017654,38.3403113688,69.4371082821,-25.2927434836,-36.6555783377,68.1472783397,-35.8461350073,-26.8104355833,-20.5193285778,3.35628454328,30.8262753871,43.3939045393,-39.9602074123,-42.2606404263,-40.9219330674,-2.9949263466,-5.8057399858,-2.49749049541,26.6656105577,-34.3585000073,14.6975233864,2.58120816581,1.75493432525,-5.85357111319,-21.1763081021,-19.1506733266,16.8309717374,0.509664337791,-1.57594759841,0.541460240357,15.2956459544,-16.0137965954,-0.0959257558928,0.375497858192,-8.85834468684,-6.97383832963,5.22992520317,-0.411986382546,8.00680557431,-4.70652887482,-1.00627643503,1.52497547784,-0.954317107374,4.92614741094,-0.538975087223,-1.40834443024,3.53846585141,14.8782187106,1.59068082374,7.378285165,-3.28461307154,-1.68316705496,-6.08606828337,-6.34092863752,-2.43450127658,13.5534269997,-2.95552474243,0.600966854858,1.27591467199,-1.03341039483,1.52141433776,-2.38266029143,-0.486539154916,2.32919253948,-1.7799411928,1.96815838462,3.24455862251,2.69556455553,1.57804181755,2.08538361405,-0.904618459247,-0.199441305848,0.114334240062,1.31957820684,1.87243811642,3.17351694594,3.46058072093],[-31809.1065246,-2400.32638817,5973.98191236,-427.959913559,2912.47378637,-749.016443319,603.560983129,1439.21612492,1074.56604632,-1373.27670044,-313.703594665,1381.92756057,-10.121267778,434.547034889,635.919976052,827.102525308,619.962298454,218.498389065,544.489968101,-174.101077489,-286.299587019,-196.06217039,108.637092747,-116.743646959,-139.76570296,363.248779856,-286.274360408,336.665145661,-1.99722338827,8.55807727676,-7.53124065005,-49.4123694575,-117.967979688,123.460993173,17.2087837517,36.355483237,65.9393845124,27.6007504449,-58.8356943976,73.2286669514,-174.365648544,-32.4641459356,-64.7881962176,-67.2101610547,45.819154861,67.2505701685,-26.4056897389,-53.812979066,67.9216599148,-39.6830500064,-33.0700596951,-16.0073441255,0.589692421357,35.0251642525,33.574558791,-39.4150933295,-41.4695158909,-44.5263934264,2.31235616263,-3.06445552902,-2.51382681498,28.3406646097,-36.3758612572,13.4425682853,3.79256252907,2.12858202768,-7.73088129301,-21.5324845014,-17.5129825007,15.6879683378,1.32168623127,-0.93292088289,1.08421645622,12.8708548388,-17.8480464767,1.22288003576,-1.2848318162,-7.5168377308,-2.84872809317,4.80813786587,0.988677286143,8.31659771329,-5.30377691164,-0.509899106687,3.11479727236,-2.69645520338,3.46286469869,0.695677089158,-0.834342796406,4.1146125554,14.3583794461,0.454161364453,6.90177098964,-5.05946223585,-0.0827877027358,-6.97951183611,-6.04681101392,-0.756150838523,13.2508274334,-3.05960858502,0.815338623851,1.472087996,-0.967578999109,2.01090174164,-1.94966779763,-0.285423458023,1.92919947626,-1.82433681965,2.68147976803,2.89026455517,2.85480841711,1.35702844276,1.16600549933,-1.31013762169,-0.357088081181,0.688123859143,1.22156676855,1.84004747318,3.5345100392,3.25985645401],[-31624.8851361,-2358.25510702,5944.05364707,-572.321111199,2948.15938215,-892.068685603,737.565657797,1301.45182186,1061.21863675,-1445.707583,-333.473727184,1319.42479749,-22.0298817864,481.399623974,588.6742326,855.070101762,623.773103419,240.750213158,584.384798188,-133.849054183,-319.241126498,-180.084605794,133.411754779,-107.748400134,-157.350721738,356.419591916,-281.467881887,303.614146688,13.9165874506,7.88424622967,-9.25269690286,-51.9936144997,-118.780032873,96.0199236218,5.26983890616,40.8134510895,60.7178471355,28.267600593,-44.003491734,71.5880185278,-190.732401565,-34.8579695093,-70.6257418524,-57.6469840277,52.9942997649,61.4489668497,-33.026659386,-68.7419240596,67.7894633578,-43.6899814,-39.6040329438,-11.2887276212,-1.15135743457,38.6886178491,23.6904839093,-38.9585535082,-38.5266609602,-45.1313381408,7.91037723305,2.43645492765,-2.78407541743,28.7116251148,-37.7251515003,12.1084275868,4.66479242576,2.21486175935,-9.15853250584,-21.5044692703,-15.6713640497,14.3910137512,2.402012687,-0.408400957556,1.99103227846,10.4290871879,-19.2748545885,2.95621671897,-2.17063346169,-5.89211226245,1.03284198531,3.2566540114,2.48815865615,8.45534252119,-6.29061653199,-0.037334268,4.71309788559,-4.38309362704,2.17190054193,1.90309736819,-0.297378351518,4.75679464408,13.5491608891,-0.518384096285,6.53132704016,-6.55738917624,1.58217579427,-7.57096435372,-5.63265199271,0.828989178444,12.4406790205,-3.11137285735,0.91931248567,1.63740279718,-0.901486149904,2.41623253984,-1.56887230205,-0.0951722376727,1.45355116135,-1.73630251661,3.35136118157,2.46316959019,3.01494013231,1.17245355053,0.257187764869,-1.63833933802,-0.477689776006,1.23465238409,1.14360755233,1.75926191835,3.81974035113,2.93410821365],[-31492.4881943,-2302.95779043,5930.3900264,-702.013759742,2942.36270645,-1011.02889015,935.12622787,1142.80221407,1044.19478484,-1486.05407887,-377.538983701,1260.04222349,14.5716016192,587.735566733,525.44758348,873.666544319,636.168572399,252.733782416,624.690146854,-107.189682706,-363.931184519,-174.185353318,154.753364084,-66.4649918706,-175.111834754,347.817968469,-265.133226405,275.455630623,32.6033439562,-1.17165170458,-7.91594131047,-62.506693683,-121.169513031,52.5333522657,8.31662246183,46.6862228646,55.2649487703,26.9728882489,-29.8230720758,76.1943283194,-208.055958785,-34.8851586167,-74.3709213381,-46.7678048327,58.9621377316,51.5646338008,-45.3727428579,-78.6725692328,68.3991308365,-47.5155248417,-45.731535797,-5.94213334839,-2.14668446756,41.2806444188,13.896172369,-38.4570702374,-33.8011754575,-42.3871049871,13.2735146483,9.91166557306,-3.64070585804,28.051450163,-38.3164754638,10.8061402574,5.08235865992,1.97311543782,-9.89912800554,-21.102380331,-13.7506650175,12.6734942476,3.782979777,-0.489458836486,3.36017368708,8.07319325643,-19.9073925868,5.0628621078,-1.97807797266,-4.21913522856,4.46478941038,0.441404277109,4.05634507202,8.36829422063,-7.78474433564,0.461653262353,6.28361132731,-5.8952508373,1.11247161167,3.10732553954,0.117826199428,5.47686973145,12.3641868832,-1.192371339,6.30695364774,-7.61335346616,3.26395283117,-7.75079720313,-5.12113834913,2.17337127462,11.1178940154,-3.09282182803,0.886783530888,1.73877669575,-0.81095849967,2.71369197452,-1.27221569164,0.0724914860338,0.938925239496,-1.48168419453,3.95374345068,1.97775007698,3.17750857357,1.02170652014,-0.548196904425,-1.89516106124,-0.558040026512,1.73894967297,1.10135052401,1.66138650975,3.98482706166,2.46390251287],[-31295.0818033,-2311.76842044,5883.91055175,-783.408464547,2962.16996595,-1093.47208858,1171.53588938,1015.35051502,1062.32268788,-1531.78384852,-435.82063584,1232.00370657,86.2441424421,708.850662124,418.058167566,885.213142327,658.94221163,265.334057398,640.89187602,-111.738087932,-404.44572231,-171.06489498,174.174208963,-42.4715917334,-196.969873172,338.030515785,-223.760180638,247.684405788,47.7620712011,-9.84976617485,-4.08795438918,-86.015749274,-128.729345047,0.566214536045,24.2657187022,53.655437653,50.5268177793,26.051601224,-18.8484177994,86.7993486378,-224.971122858,-31.6962300361,-71.0726477177,-34.7302095375,59.5665906592,35.8063871633,-61.2897775625,-79.7750528336,70.112101112,-50.3373227053,-49.5655442128,0.0220481014083,-3.26525406051,42.4235314386,4.61475312138,-36.7034876979,-26.6836583329,-36.2735933344,18.6288343002,18.195140999,-5.58723532364,27.8549454265,-37.7067840001,9.60397414554,5.18333458172,1.60122661412,-9.84682218225,-20.3409995162,-11.9511658735,10.5086327004,5.71595583857,-1.29309844568,5.34980314929,6.23850412889,-19.2157198788,7.44076671912,-0.245035107432,-2.5223426232,7.28244854943,-3.3176873799,5.68146281958,8.10582054129,-9.86365635173,1.02388996647,7.807353958,-7.15612296169,0.389589178156,4.36280891982,0.413472622436,6.34819948985,10.8465781835,-1.45788502053,6.33197481025,-7.99058113705,4.96567959632,-7.44603329898,-4.45599005196,3.00412299701,9.34781120249,-2.98343858136,0.732966725511,1.74673000344,-0.663931822563,2.88514057305,-1.10289034598,0.208889353421,0.412064456907,-1.01545156616,4.49601074601,1.47606614988,3.33735832004,0.926268594228,-1.15258863851,-2.06692292277,-0.628022917441,2.19975253888,1.08842806278,1.56432246702,3.97297234311,1.81073946622],[-31029.2518816,-2336.35849454,5818.49782661,-843.358614885,2962.10398161,-1215.37971353,1396.93251292,842.803248027,1111.80607433,-1595.62663149,-498.034770868,1210.47700764,120.045180645,834.029105211,280.088461539,892.204548723,692.847314726,272.793507175,618.858353394,-149.886974885,-428.332498472,-143.005005547,219.410742862,-52.9405485771,-223.853922973,330.100992778,-165.164326115,216.140291712,54.6034511291,-19.4475181328,-6.86245083331,-112.947841998,-131.077875411,-46.3081457771,46.6579391804,61.0940232031,47.3764676805,24.4778925809,-11.7610550034,97.5788542558,-240.088797207,-22.2952550031,-59.7296484731,-19.502493396,50.9693624067,16.8323079238,-79.5669810849,-69.65212764,73.09048034,-51.4479255882,-49.3979685405,5.55114902313,-5.64010846047,40.970868341,-3.89950229288,-33.8706007874,-17.4332736728,-28.4933355429,24.170978795,23.4221849608,-9.30486626511,27.8311835388,-35.5747554173,8.58114726783,5.28928168646,1.74570333937,-9.10159715308,-19.138046757,-10.7100160421,8.12322681454,7.5985443211,-2.99803738808,7.57639685414,5.11879039254,-17.3760595922,9.9904582152,2.5101157756,-1.07657336629,9.35035948879,-7.46156698548,7.30653341843,7.80222978356,-12.4343484485,1.6631983598,9.30872884351,-8.18889669411,0.0816134114697,5.62566090481,0.478548290724,7.20083654679,8.91597397011,-1.38904293792,6.5945426442,-7.64150058662,6.59047201292,-6.587529401,-3.6299087023,3.16989590898,7.29448858307,-2.77744143423,0.497074995608,1.66800777591,-0.425394417215,2.93511565447,-1.10250066901,0.298857083503,-0.120499787512,-0.339889064427,4.97139134265,0.910513526069,3.49720204905,0.884593017178,-1.49709824771,-2.15430037768,-0.697198886696,2.60068129468,1.14346901802,1.48879725196,3.72839596299,0.971518993019],[-30788.2800342,-2312.67508552,5786.30187143,-962.803335925,2979.60643828,-1388.49892262,1525.98616789,663.126294952,1176.87421625,-1693.40136508,-527.684836451,1199.27376099,144.906376765,912.534365462,162.060402325,906.210870526,732.73206859,256.508495568,593.862283527,-214.024105865,-431.262353313,-105.887843889,254.684439221,-93.134606754,-247.515155951,330.44579701,-106.223209434,192.318682161,63.6309543624,-25.6280539946,-28.523315549,-132.1498015,-128.09867233,-69.1410481769,65.3199380651,63.9531879943,45.5300354379,17.7129462251,-8.06447746225,104.476810499,-251.892544222,-6.12798624452,-42.0631157292,-10.5429518634,37.740345742,1.94265139151,-95.3383122407,-54.7597593499,75.2393351774,-51.8553335984,-46.6938227282,8.01944314639,-10.289436839,36.062539967,-10.1512972805,-31.2079505034,-9.22221401553,-20.3295888062,29.3504646057,23.8691592927,-13.921316338,26.7165014535,-32.1422443671,7.67241524858,5.32562487055,2.9615297901,-8.24686875347,-17.5353093941,-10.4486089905,6.33288824626,8.28866439291,-5.53145143316,9.29127863779,4.34566331029,-14.8964859243,12.8494832137,5.48753308099,-0.0363374679185,10.4132230985,-11.3088910852,8.72946409878,7.50535800866,-15.2422446729,2.24611302215,10.8006717201,-9.10971996062,0.263708371128,6.80290621141,0.340579011733,7.63915039029,6.49060335374,-1.14342214879,7.09184676469,-6.64365565982,8.13943122405,-5.19480606412,-2.72664963501,2.74683138186,5.28220369573,-2.5006276262,0.165553920224,1.52271469462,-0.0982023532088,2.87831473898,-1.28673598147,0.361998941586,-0.646224171485,0.505113058533,5.34871117168,0.211169265142,3.67421415543,0.86433583229,-1.5497163352,-2.17384600942,-0.717388399051,2.9564758575,1.28765653544,1.43561669975,3.28562274943,-0.012700092837],[-30649.13763,-2287.66289005,5805.21623251,-1122.77938472,2972.72527823,-1588.14472762,1578.64396953,549.600685896,1239.41029019,-1792.58120223,-538.262308483,1229.97130185,171.995720456,916.612166119,30.4855102851,929.803623213,774.595352376,207.045719326,555.333644873,-272.772391397,-417.817839957,-67.0434012898,290.95500099,-133.362699374,-256.353867615,339.077999652,-54.5639939936,185.611092545,78.4976400296,-24.4185621924,-57.3091986581,-146.322478114,-124.178898972,-78.4818974758,71.3991339096,60.5097613408,46.7801477355,8.90547924804,-5.23730823573,107.75594449,-259.117986136,17.5767304101,-24.0758526376,-9.68447999856,21.1138823958,-8.32900145769,-104.137834119,-38.8400918966,75.3955487834,-51.9911367746,-44.4162463391,7.44915539898,-16.0546465209,28.1619309747,-12.0770183744,-30.5717316531,-3.19385515501,-14.0362015853,30.9770248703,21.5287703576,-17.0221592641,23.7261135755,-27.8384986269,7.12987787083,5.2703407553,5.00380183787,-7.41783610171,-15.8438201827,-11.2626742501,5.76969570914,6.66267125303,-8.31099133652,9.81727797047,3.22702063663,-11.9173083353,15.805047495,8.55010789756,0.403338989864,10.3092754032,-14.2134019876,9.68917007976,7.2833348178,-17.9711377171,2.63577278346,12.1853036139,-10.0474023389,1.05314950965,7.68297847614,0.115763503354,7.2664156673,3.52519056025,-0.905330888141,7.71369752438,-5.06305838964,9.61320680915,-3.35961811984,-2.03888169975,1.87796902959,3.60646084863,-2.22036796588,-0.309165602664,1.35757086899,0.291744899285,2.72759502848,-1.64637545556,0.474273481829,-1.16420256711,1.48348503734,5.55514328086,-0.625908291773,3.84530065475,0.793970422169,-1.33941511531,-2.12692825318,-0.636091045894,3.27194249223,1.50466821901,1.35167607446,2.71833780734,-1.09562441488]])
    return models,coeffs

def get_arch3k():
    models=[-1000,-990,-980,-970,-960,-950,-940,-930,-920,-910,-900,-890,-880,-870,-860,-850,-840,-830,-820,-810,-800,-790,-780,-770,-760,-750,-740,-730,-720,-710,-700,-690,-680,-670,-660,-650,-640,-630,-620,-610,-600,-590,-580,-570,-560,-550,-540,-530,-520,-510,-500,-490,-480,-470,-460,-450,-440,-430,-420,-410,-400,-390,-380,-370,-360,-350,-340,-330,-320,-310,-300,-290,-280,-270,-260,-250,-240,-230,-220,-210,-200,-190,-180,-170,-160,-150,-140,-130,-120,-110,-100,-90,-80,-70,-60,-50,-40,-30,-20,-10,0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,310,320,330,340,350,360,370,380,390,400,410,420,430,440,450,460,470,480,490,500,510,520,530,540,550,560,570,580,590,600,610,620,630,640,650,660,670,680,690,700,710,720,730,740,750,760,770,780,790,800,810,820,830,840,850,860,870,880,890,900,910,920,930,940,950,960,970,980,990,1000,1010,1020,1030,1040,1050,1060,1070,1080,1090,1100,1110,1120,1130,1140,1150,1160,1170,1180,1190,1200,1210,1220,1230,1240,1250,1260,1270,1280,1290,1300,1310,1320,1330,1340,1350,1360,1370,1380,1390,1400,1410,1420,1430,1440,1450,1460,1470,1480,1490,1500,1510,1520,1530,1540,1550,1560,1570,1580,1590,1600,1610,1620,1630,1640,1650,1660,1670,1680,1690,1700,1710,1720,1730,1740,1750,1760,1770,1780,1790,1800,1810,1820,1830,1840,1850,1860,1870,1880,1890,1900,1910,1920,1930,1940]
    return models,coeffs

def get_pfm9k():
    models=[-7000,-6990,-6980,-6970,-6960,-6950,-6940,-6930,-6920,-6910,-6900,-6890,-6880,-6870,-6860,-6850,-6840,-6830,-6820,-6810,-6800,-6790,-6780,-6770,-6760,-6750,-6740,-6730,-6720,-6710,-6700,-6690,-6680,-6670,-6660,-6650,-6640,-6630,-6620,-6610,-6600,-6590,-6580,-6570,-6560,-6550,-6540,-6530,-6520,-6510,-6500,-6490,-6480,-6470,-6460,-6450,-6440,-6430,-6420,-6410,-6400,-6390,-6380,-6370,-6360,-6350,-6340,-6330,-6320,-6310,-6300,-6290,-6280,-6270,-6260,-6250,-6240,-6230,-6220,-6210,-6200,-6190,-6180,-6170,-6160,-6150,-6140,-6130,-6120,-6110,-6100,-6090,-6080,-6070,-6060,-6050,-6040,-6030,-6020,-6010,-6000,-5990,-5980,-5970,-5960,-5950,-5940,-5930,-5920,-5910,-5900,-5890,-5880,-5870,-5860,-5850,-5840,-5830,-5820,-5810,-5800,-5790,-5780,-5770,-5760,-5750,-5740,-5730,-5720,-5710,-5700,-5690,-5680,-5670,-5660,-5650,-5640,-5630,-5620,-5610,-5600,-5590,-5580,-5570,-5560,-5550,-5540,-5530,-5520,-5510,-5500,-5490,-5480,-5470,-5460,-5450,-5440,-5430,-5420,-5410,-5400,-5390,-5380,-5370,-5360,-5350,-5340,-5330,-5320,-5310,-5300,-5290,-5280,-5270,-5260,-5250,-5240,-5230,-5220,-5210,-5200,-5190,-5180,-5170,-5160,-5150,-5140,-5130,-5120,-5110,-5100,-5090,-5080,-5070,-5060,-5050,-5040,-5030,-5020,-5010,-5000,-4990,-4980,-4970,-4960,-4950,-4940,-4930,-4920,-4910,-4900,-4890,-4880,-4870,-4860,-4850,-4840,-4830,-4820,-4810,-4800,-4790,-4780,-4770,-4760,-4750,-4740,-4730,-4720,-4710,-4700,-4690,-4680,-4670,-4660,-4650,-4640,-4630,-4620,-4610,-4600,-4590,-4580,-4570,-4560,-4550,-4540,-4530,-4520,-4510,-4500,-4490,-4480,-4470,-4460,-4450,-4440,-4430,-4420,-4410,-4400,-4390,-4380,-4370,-4360,-4350,-4340,-4330,-4320,-4310,-4300,-4290,-4280,-4270,-4260,-4250,-4240,-4230,-4220,-4210,-4200,-4190,-4180,-4170,-4160,-4150,-4140,-4130,-4120,-4110,-4100,-4090,-4080,-4070,-4060,-4050,-4040,-4030,-4020,-4010,-4000,-3990,-3980,-3970,-3960,-3950,-3940,-3930,-3920,-3910,-3900,-3890,-3880,-3870,-3860,-3850,-3840,-3830,-3820,-3810,-3800,-3790,-3780,-3770,-3760,-3750,-3740,-3730,-3720,-3710,-3700,-3690,-3680,-3670,-3660,-3650,-3640,-3630,-3620,-3610,-3600,-3590,-3580,-3570,-3560,-3550,-3540,-3530,-3520,-3510,-3500,-3490,-3480,-3470,-3460,-3450,-3440,-3430,-3420,-3410,-3400,-3390,-3380,-3370,-3360,-3350,-3340,-3330,-3320,-3310,-3300,-3290,-3280,-3270,-3260,-3250,-3240,-3230,-3220,-3210,-3200,-3190,-3180,-3170,-3160,-3150,-3140,-3130,-3120,-3110,-3100,-3090,-3080,-3070,-3060,-3050,-3040,-3030,-3020,-3010,-3000,-2990,-2980,-2970,-2960,-2950,-2940,-2930,-2920,-2910,-2900,-2890,-2880,-2870,-2860,-2850,-2840,-2830,-2820,-2810,-2800,-2790,-2780,-2770,-2760,-2750,-2740,-2730,-2720,-2710,-2700,-2690,-2680,-2670,-2660,-2650,-2640,-2630,-2620,-2610,-2600,-2590,-2580,-2570,-2560,-2550,-2540,-2530,-2520,-2510,-2500,-2490,-2480,-2470,-2460,-2450,-2440,-2430,-2420,-2410,-2400,-2390,-2380,-2370,-2360,-2350,-2340,-2330,-2320,-2310,-2300,-2290,-2280,-2270,-2260,-2250,-2240,-2230,-2220,-2210,-2200,-2190,-2180,-2170,-2160,-2150,-2140,-2130,-2120,-2110,-2100,-2090,-2080,-2070,-2060,-2050,-2040,-2030,-2020,-2010,-2000,-1990,-1980,-1970,-1960,-1950,-1940,-1930,-1920,-1910,-1900,-1890,-1880,-1870,-1860,-1850,-1840,-1830,-1820,-1810,-1800,-1790,-1780,-1770,-1760,-1750,-1740,-1730,-1720,-1710,-1700,-1690,-1680,-1670,-1660,-1650,-1640,-1630,-1620,-1610,-1600,-1590,-1580,-1570,-1560,-1550,-1540,-1530,-1520,-1510,-1500,-1490,-1480,-1470,-1460,-1450,-1440,-1430,-1420,-1410,-1400,-1390,-1380,-1370,-1360,-1350,-1340,-1330,-1320,-1310,-1300,-1290,-1280,-1270,-1260,-1250,-1240,-1230,-1220,-1210,-1200,-1190,-1180,-1170,-1160,-1150,-1140,-1130,-1120,-1110,-1100,-1090,-1080,-1070,-1060,-1050,-1040,-1030,-1020,-1010,-1000,-990,-980,-970,-960,-950,-940,-930,-920,-910,-900,-890,-880,-870,-860,-850,-840,-830,-820,-810,-800,-790,-780,-770,-760,-750,-740,-730,-720,-710,-700,-690,-680,-670,-660,-650,-640,-630,-620,-610,-600,-590,-580,-570,-560,-550,-540,-530,-520,-510,-500,-490,-480,-470,-460,-450,-440,-430,-420,-410,-400,-390,-380,-370,-360,-350,-340,-330,-320,-310,-300,-290,-280,-270,-260,-250,-240,-230,-220,-210,-200,-190,-180,-170,-160,-150,-140,-130,-120,-110,-100,-90,-80,-70,-60,-50,-40,-30,-20,-10,0,10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300,310,320,330,340,350,360,370,380,390,400,410,420,430,440,450,460,470,480,490,500,510,520,530,540,550,560,570,580,590,600,610,620,630,640,650,660,670,680,690,700,710,720,730,740,750,760,770,780,790,800,810,820,830,840,850,860,870,880,890,900,910,920,930,940,950,960,970,980,990,1000,1010,1020,1030,1040,1050,1060,1070,1080,1090,1100,1110,1120,1130,1140,1150,1160,1170,1180,1190,1200,1210,1220,1230,1240,1250,1260,1270,1280,1290,1300,1310,1320,1330,1340,1350,1360,1370,1380,1390,1400,1410,1420,1430,1440,1450,1460,1470,1480,1490,1500,1510,1520,1530,1540,1550,1560,1570,1580,1590,1600,1610,1620,1630,1640,1650,1660,1670,1680,1690,1700,1710,1720,1730,1740,1750,1760,1770,1780,1790,1800,1810,1820,1830,1840,1850,1860,1870,1880,1890,1900]
    return models,coeffs

def get_cals10k():
    models= ['-9950', '-9900', '-9850', '-9800', '-9750', '-9700', '-9650', '-9600', '-9550', '-9500', '-9450', '-9400', '-9350', '-9300', '-9250', '-9200', '-9150', '-9100', '-9050', '-9000', '-8950', '-8900', '-8850', '-8800', '-8750', '-8700', '-8650', '-8600', '-8550', '-8500', '-8450', '-8400', '-8350', '-8300', '-8250', '-8200', '-8150', '-8100', '-8050', '-8000', '-7950', '-7900', '-7850', '-7800', '-7750', '-7700', '-7650', '-7600', '-7550', '-7500', '-7450', '-7400', '-7350', '-7300', '-7250', '-7200', '-7150', '-7100', '-7050', '-7000', '-6950', '-6900', '-6850', '-6800', '-6750', '-6700', '-6650', '-6600', '-6550', '-6500', '-6450', '-6400', '-6350', '-6300', '-6250', '-6200', '-6150', '-6100', '-6050', '-6000', '-5950', '-5900', '-5850', '-5800', '-5750', '-5700', '-5650', '-5600', '-5550', '-5500', '-5450', '-5400', '-5350', '-5300', '-5250', '-5200', '-5150', '-5100', '-5050', '-5000', '-4950', '-4900', '-4850', '-4800', '-4750', '-4700', '-4650', '-4600', '-4550', '-4500', '-4450', '-4400', '-4350', '-4300', '-4250', '-4200', '-4150', '-4100', '-4050', '-4000', '-3950', '-3900', '-3850', '-3800', '-3750', '-3700', '-3650', '-3600', '-3550', '-3500', '-3450', '-3400', '-3350', '-3300', '-3250', '-3200', '-3150', '-3100', '-3050', '-3000', '-2950', '-2900', '-2850', '-2800', '-2750', '-2700', '-2650', '-2600', '-2550', '-2500', '-2450', '-2400', '-2350', '-2300', '-2250', '-2200', '-2150', '-2100', '-2050', '-2000', '-1950', '-1900', '-1850', '-1800', '-1750', '-1700', '-1650', '-1600', '-1550', '-1500', '-1450', '-1400', '-1350', '-1300', '-1250', '-1200', '-1150', '-1100', '-1050', '-1000', '-950', '-900', '-850', '-800', '-750', '-700', '-650', '-600', '-550', '-500', '-450', '-400', '-350', '-300', '-250', '-200', '-150', '-100', '-50', '0', '50', '100', '150', '200', '250', '300', '350', '400', '450', '500', '550', '600', '650', '700', '750', '800', '850', '900', '950', '1000', '1050', '1100', '1150', '1200', '1250', '1300', '1350', '1400', '1450', '1500', '1550', '1600', '1650', '1700', '1750', '1800', '1850', '1900', '1950']
    return models,coeffs


def unpack(gh):
    """
    unpacks gh list into l m g h type list
    """
    data=[]
    k,l=0,1
    while k+1<len(gh):
        for m in range(l+1):
            if m==0:
                data.append([l,m,gh[k],0])
                k+=1
            else:
                data.append([l,m,gh[k],gh[k+1]])
                k+=2
    return data


def magsyn(gh,sv,b,date,itype,alt,colat,elong):
    """
# Computes x, y, z, and f for a given date and position, from the
# spherical harmonic coeifficients of the International Geomagnetic
# Reference Field (IGRF).
# From Malin and Barraclough (1981), Computers and Geosciences, V.7, 401-405.
#
# Input:
#       date  = Required date in years and decimals of a year (A.D.)
#       itype = 1, if geodetic coordinates are used, 2 if geocentric
#       alt   = height above mean sea level in km (if itype = 1)
#       alt   = radial distance from the center of the earth (itype = 2)
#       colat = colatitude in degrees (0 to 180)
#       elong = east longitude in degrees (0 to 360)
#               gh        = main field values for date (calc. in igrf subroutine)
#               sv        = secular variation coefficients (calc. in igrf subroutine)
#               begin = date of dgrf (or igrf) field prior to required date
#
# Output:
#       x     - north component of the magnetic force in nT
#       y     - east component of the magnetic force in nT
#       z     - downward component of the magnetic force in nT
#       f     - total magnetic force in nT
#
#       NB: the coordinate system for x,y, and z is the same as that specified
#       by itype.
#
# Modified 4/9/97 to use DGRFs from 1945 to 1990 IGRF
# Modified 10/13/06 to use  1995 DGRF, 2005 IGRF and sv coefficient
# for extrapolation beyond 2005. Coefficients from Barton et al. PEPI, 97: 23-26
# (1996), via web site for NOAA, World Data Center A. Modified to use
#degree and
# order 10 as per notes in Malin and Barraclough (1981).
# coefficients for DGRF 1995 and IGRF 2005 are from http://nssdcftp.gsfc.nasa.gov/models/geomagnetic/igrf/fortran_code/
# igrf subroutine calculates
# the proper main field and secular variation coefficients (interpolated between
# dgrf values or extrapolated from 1995 sv values as appropriate).
    """
#
#       real gh(120),sv(120),p(66),q(66),cl(10),sl(10)
#               real begin,dateq
    p=numpy.zeros((66),'f')
    q=numpy.zeros((66),'f')
    cl=numpy.zeros((10),'f')
    sl=numpy.zeros((10),'f')
    begin=b
    t = date - begin
    r = alt
    one = colat*0.0174532925
    ct = numpy.cos(one)
    st = numpy.sin(one)
    one = elong*0.0174532925
    cl[0] = numpy.cos(one)
    sl[0] = numpy.sin(one)
    x,y,z = 0.0,0.0,0.0
    cd,sd = 1.0,0.0
    l,ll,m,n = 1,0,1,0
    if itype!=2:
#
# if required, convert from geodectic to geocentric
        a2 = 40680925.0
        b2 = 40408585.0
        one = a2 * st * st
        two = b2 * ct * ct
        three = one + two
        rho = numpy.sqrt(three)
        r = numpy.sqrt(alt*(alt+2.0*rho) + (a2*one+b2*two)/three)
        cd = (alt + rho) /r
        sd = (a2 - b2) /rho * ct * st /r
        one = ct
        ct = ct*cd - st*sd
        st  = st*cd + one*sd
    ratio = 6371.2 /r
    rr = ratio * ratio
#
# compute Schmidt quasi-normal coefficients p and x(=q)
    p[0] = 1.0
    p[2] = st
    q[0] = 0.0
    q[2] = ct
    for k in range(1,66):
        if n < m:   # else go to 2
            m = 0
            n = n + 1
            rr = rr * ratio
            fn = n
            gn = n - 1
# 2
        fm = m
        if k != 2: # else go to 4
            if m == n:   # else go to 3
                one = numpy.sqrt(1.0 - 0.5/fm)
                j = k - n - 1
                p[k] = one * st * p[j]
                q[k] = one * (st*q[j] + ct*p[j])
                cl[m-1] = cl[m-2]*cl[0] - sl[m-2]*sl[0]
                sl[m-1] = sl[m-2]*cl[0] + cl[m-2]*sl[0]
            else:
# 3
                gm = m * m
                one = numpy.sqrt(fn*fn - gm)
                two = numpy.sqrt(gn*gn - gm) /one
                three = (fn + gn) /one
                i = k - n
                j = i - n + 1
                p[k] = three*ct*p[i] - two*p[j]
                q[k] = three*(ct*q[i] - st*p[i]) - two*q[j]
#
# synthesize x, y, and z in geocentric coordinates.
# 4
        one = (gh[l-1] + sv[ll+l-1]*t)*rr
        if m != 0: # else go to 7
            two = (gh[l] + sv[ll+l]*t)*rr
            three = one*cl[m-1] + two*sl[m-1]
            x = x + three*q[k]
            z = z - (fn + 1.0)*three*p[k]
            if st != 0.0: # else go to 5
                y = y + (one*sl[m-1] - two*cl[m-1])*fm*p[k]/st
            else:
# 5
                y = y + (one*sl[m-1] - two*cl[m-1])*q[k]*ct
            l = l + 2
        else:
# 7
            x = x + one*q[k]
            z = z - (fn + 1.0)*one*p[k]
            l = l + 1
        m = m + 1
#
# convert to coordinate system specified by itype
    one = x
    x = x*cd + z*sd
    z = z*cd - one*sd
    f = numpy.sqrt(x*x + y*y + z*z)
#
    return x,y,z,f
#
#
def measurements_methods(meas_data,noave):
    """
    get list of unique specs
    """
#
    version_num=get_version()
    sids=get_specs(meas_data)
# list  of measurement records for this specimen
#
# step through spec by spec
#
    SpecTmps,SpecOuts=[],[]
    for spec in sids:
        TRM,IRM3D,ATRM,CR=0,0,0,0
        expcodes=""
# first collect all data for this specimen and do lab treatments
        SpecRecs=get_dictitem(meas_data,'er_specimen_name',spec,'T') # list  of measurement records for this specimen
        for rec in SpecRecs:
            if 'measurement_flag' not in rec.keys():rec['measurement_flag']='g'
            tmpmeths=rec['magic_method_codes'].split(":")
            meths=[]
            if "LP-TRM" in tmpmeths:TRM=1 # catch these suckers here!
            if "LP-IRM-3D" in tmpmeths:
                IRM3D=1 # catch these suckers here!
            elif "LP-AN-TRM" in tmpmeths:
                ATRM=1 # catch these suckers here!
            elif "LP-CR-TRM" in tmpmeths:
                CR=1 # catch these suckers here!
#
# otherwise write over existing method codes
#
# find NRM data (LT-NO)
#
            elif float(rec["measurement_temp"])>=273. and float(rec["measurement_temp"]) < 323.:
# between 0 and 50C is room T measurement
                if ("measurement_dc_field" not in rec.keys() or float(rec["measurement_dc_field"])==0 or rec["measurement_dc_field"]=="") and ("measurement_ac_field" not in rec.keys() or float(rec["measurement_ac_field"])==0 or rec["measurement_ac_field"]==""):
# measurement done in zero field!
                    if  "treatment_temp" not in rec.keys() or rec["treatment_temp"].strip()=="" or (float(rec["treatment_temp"])>=273. and float(rec["treatment_temp"]) < 298.):
# between 0 and 50C is room T treatment
                        if "treatment_ac_field" not in rec.keys() or rec["treatment_ac_field"] =="" or float(rec["treatment_ac_field"])==0:
# no AF
                            if "treatment_dc_field" not in rec.keys() or rec["treatment_dc_field"]=="" or float(rec["treatment_dc_field"])==0:# no IRM!
                                if "LT-NO" not in meths:meths.append("LT-NO")
                            elif "LT-IRM" not in meths:
                                meths.append("LT-IRM") # it's an IRM
#
# find AF/infield/zerofield
#
                        elif "treatment_dc_field" not in rec.keys() or rec["treatment_dc_field"]=="" or float(rec["treatment_dc_field"])==0: # no ARM
                            if "LT-AF-Z" not in meths:meths.append("LT-AF-Z")
                        else: # yes ARM
                            if "LT-AF-I" not in meths: meths.append("LT-AF-I")
#
# find Thermal/infield/zerofield
#
                    elif float(rec["treatment_temp"])>=323:  # treatment done at  high T
                        if TRM==1:
                            if "LT-T-I" not in meths: meths.append("LT-T-I") # TRM - even if zero applied field!
                        elif "treatment_dc_field" not in rec.keys() or rec["treatment_dc_field"]=="" or float(rec["treatment_dc_field"])==0.: # no TRM
                            if  "LT-T-Z" not in meths: meths.append("LT-T-Z") # don't overwrite if part of a TRM experiment!
                        else: # yes TRM
                            if "LT-T-I" not in meths: meths.append("LT-T-I")
#
# find low-T infield,zero field
#
                    else:  # treatment done at low T
                        if "treatment_dc_field" not in rec.keys() or rec["treatment_dc_field"]=="" or float(rec["treatment_dc_field"])==0: # no field
                            if "LT-LT-Z" not in meths:meths.append("LT-LT-Z")
                        else: # yes field
                            if "LT-LT-I" not in meths:meths.append("LT-LT-I")
                if "measurement_chi_volume" in rec.keys() or "measurement_chi_mass" in rec.keys():
                    if  "LP-X" not in meths:meths.append("LP-X")
                elif "measurement_lab_dc_field" in rec.keys() and rec["measurement_lab_dc_field"]!=0: # measurement in presence of dc field and not susceptibility; hysteresis!
                    if  "LP-HYS" not in meths:
                        hysq=raw_input("Is this a hysteresis experiment? [1]/0")
                        if hysq=="" or hysq=="1":
                            meths.append("LP-HYS")
                        else:
                            metha=raw_input("Enter the lab protocol code that best describes this experiment ")
                            meths.append(metha)
                methcode=""
                for meth in meths:
                    methcode=methcode+meth.strip()+":"
                rec["magic_method_codes"]=methcode[:-1] # assign them back
#
# done with first pass, collect and assign provisional method codes
            if "measurement_description" not in rec.keys():rec["measurement_description"]=""
            rec["er_citation_names"]="This study"
            SpecTmps.append(rec)
# ready for second pass through, step through specimens, check whether ptrm, ptrm tail checks, or AARM, etc.
#
    for spec in sids:
        MD,pTRM,IZ,ZI=0,0,0,0 # these are flags for the lab protocol codes
        expcodes=""
        NewSpecs,SpecMeths=[],[]
        experiment_name,measnum="",1
        if IRM3D==1:experiment_name="LP-IRM-3D"
        if ATRM==1: experiment_name="LP-AN-TRM"
        if CR==1: experiment_name="LP-CR"
        NewSpecs=get_dictitem(SpecTmps,'er_specimen_name',spec,'T')
#
# first look for replicate measurements
#
        Ninit=len(NewSpecs)
        if noave!=1:
            vdata,treatkeys=vspec_magic(NewSpecs) # averages replicate measurements, returns treatment keys that are being used
            if len(vdata)!=len(NewSpecs):
                #print spec,'started with ',Ninit,' ending with ',len(vdata)
                NewSpecs=vdata
                #print "Averaged replicate measurements"
#
# now look through this specimen's records - try to figure out what experiment it is
#
        if len(NewSpecs)>1: # more than one meas for this spec - part of an unknown experiment
            SpecMeths=get_list(NewSpecs,'magic_method_codes').split(":")
            if "LT-T-I" in  SpecMeths and experiment_name=="": # TRM steps, could be TRM acquisition, Shaw or a Thellier experiment or TDS experiment
    #
    # collect all the infield steps and look for changes in dc field vector
    #
                Steps,TI=[],1
                for rec in  NewSpecs:
                    methods=get_list(NewSpecs,'magic_method_codes').split(":")
                    if "LT-T-I" in methods:Steps.append(rec)  # get all infield steps together
                rec_bak=Steps[0]
                if "treatment_dc_field_phi" in rec_bak.keys() and "treatment_dc_field_theta" in rec_bak.keys():
                    if rec_bak["treatment_dc_field_phi"] !="" and rec_bak["treatment_dc_field_theta"]!="":   # at least there is field orientation info
                        phi0,theta0=rec_bak["treatment_dc_field_phi"],rec_bak["treatment_dc_field_theta"]
                        for k in range(1,len(Steps)):
                            rec=Steps[k]
                            phi,theta=rec["treatment_dc_field_phi"],rec["treatment_dc_field_theta"]
                            if phi!=phi0 or theta!=theta0: ANIS=1   # if direction changes, is some sort of anisotropy experiment
                if "LT-AF-I" in SpecMeths and "LT-AF-Z" in SpecMeths: # must be Shaw :(
                    experiment_name="LP-PI-TRM:LP-PI-ALT-AFARM"
                elif TRM==1:
                    experiment_name="LP-TRM"
            else: TI= 0 # no infield steps at all
            if "LT-T-Z" in  SpecMeths and experiment_name=="": # thermal demag steps
                if TI==0:
                    experiment_name="LP-DIR-T" # just ordinary thermal demag
                elif TRM!=1: # heart pounding - could be some  kind of TRM normalized paleointensity or LP-TRM-TD experiment
                    Temps=[]
                    for step in Steps: # check through the infield steps - if all at same temperature, then must be a demag of a total TRM with checks
                        if step['treatment_temp'] not in Temps:Temps.append(step['treatment_temp'])
                    if len(Temps)>1:
                        experiment_name="LP-PI-TRM" # paleointensity normalized by TRM
                    else:
                        experiment_name="LP-TRM-TD" # thermal demag of a lab TRM (could be part of a LP-PI-TDS experiment)
                TZ=1
            else: TZ= 0 # no zero field steps at all
            if "LT-AF-I" in  SpecMeths: # ARM steps
                Steps=[]
                for rec in  NewSpecs:
                    tmp=rec["magic_method_codes"].split(":")
                    methods=[]
                    for meth in tmp:
                        methods.append(meth.strip())
                    if "LT-AF-I" in methods:Steps.append(rec)  # get all infield steps together
                rec_bak=Steps[0]
                if "treatment_dc_field_phi" in rec_bak.keys() and "treatment_dc_field_theta" in rec_bak.keys():
                    if rec_bak["treatment_dc_field_phi"] !="" and rec_bak["treatment_dc_field_theta"]!="":   # at least there is field orientation info
                        phi0,theta0=rec_bak["treatment_dc_field_phi"],rec_bak["treatment_dc_field_theta"]
                        ANIS=0
                        for k in range(1,len(Steps)):
                            rec=Steps[k]
                            phi,theta=rec["treatment_dc_field_phi"],rec["treatment_dc_field_theta"]
                            if phi!=phi0 or theta!=theta0: ANIS=1   # if direction changes, is some sort of anisotropy experiment
                        if ANIS==1:
                            experiment_name="LP-AN-ARM"
                if experiment_name=="":  # not anisotropy of ARM - acquisition?
                        field0=rec_bak["treatment_dc_field"]
                        ARM=0
                        for k in range(1,len(Steps)):
                            rec=Steps[k]
                            field=rec["treatment_dc_field"]
                            if field!=field0: ARM=1
                        if ARM==1:
                            experiment_name="LP-ARM"
                AFI=1
            else: AFI= 0 # no ARM steps at all
            if "LT-AF-Z" in  SpecMeths and experiment_name=="": # AF demag steps
                if AFI==0:
                    experiment_name="LP-DIR-AF" # just ordinary AF demag
                else: # heart pounding - a pseudothellier?
                    experiment_name="LP-PI-ARM"
                AFZ=1
            else: AFZ= 0 # no AF demag at all
            if "LT-IRM" in SpecMeths: # IRM
                Steps=[]
                for rec in  NewSpecs:
                    tmp=rec["magic_method_codes"].split(":")
                    methods=[]
                    for meth in tmp:
                        methods.append(meth.strip())
                    if "LT-IRM" in methods:Steps.append(rec)  # get all infield steps together
                rec_bak=Steps[0]
                if "treatment_dc_field_phi" in rec_bak.keys() and "treatment_dc_field_theta" in rec_bak.keys():
                    if rec_bak["treatment_dc_field_phi"] !="" and rec_bak["treatment_dc_field_theta"]!="":   # at least there is field orientation info
                        phi0,theta0=rec_bak["treatment_dc_field_phi"],rec_bak["treatment_dc_field_theta"]
                        ANIS=0
                        for k in range(1,len(Steps)):
                            rec=Steps[k]
                            phi,theta=rec["treatment_dc_field_phi"],rec["treatment_dc_field_theta"]
                            if phi!=phi0 or theta!=theta0: ANIS=1   # if direction changes, is some sort of anisotropy experiment
                        if ANIS==1:experiment_name="LP-AN-IRM"
                if experiment_name=="":  # not anisotropy of IRM - acquisition?
                    field0=rec_bak["treatment_dc_field"]
                    IRM=0
                    for k in range(1,len(Steps)):
                        rec=Steps[k]
                        field=rec["treatment_dc_field"]
                        if field!=field0: IRM=1
                    if IRM==1:experiment_name="LP-IRM"
                IRM=1
            else: IRM=0 # no IRM at all
            if "LP-X" in SpecMeths: # susceptibility run
                Steps=get_dictitem(NewSpecs,'magic_method_codes','LT-X','has')
                if len(Steps)>0:
                    rec_bak=Steps[0]
                    if "treatment_dc_field_phi" in rec_bak.keys() and "treatment_dc_field_theta" in rec_bak.keys():
                        if rec_bak["treatment_dc_field_phi"] !="" and rec_bak["treatment_dc_field_theta"]!="":   # at least there is field orientation info
                            phi0,theta0=rec_bak["treatment_dc_field_phi"],rec_bak["treatment_dc_field_theta"]
                            ANIS=0
                            for k in range(1,len(Steps)):
                                rec=Steps[k]
                                phi,theta=rec["treatment_dc_field_phi"],rec["treatment_dc_field_theta"]
                                if phi!=phi0 or theta!=theta0: ANIS=1   # if direction changes, is some sort of anisotropy experiment
                            if ANIS==1:experiment_name="LP-AN-MS"
            else: CHI=0 # no susceptibility at all
    #
    # now need to deal with special thellier experiment problems - first clear up pTRM checks and  tail checks
    #
            if experiment_name=="LP-PI-TRM": # is some sort of thellier experiment
                rec_bak=NewSpecs[0]
                tmp=rec_bak["magic_method_codes"].split(":")
                methbak=[]
                for meth in tmp:
                    methbak.append(meth.strip()) # previous steps method codes
                for k in range(1,len(NewSpecs)):
                    rec=NewSpecs[k]
                    tmp=rec["magic_method_codes"].split(":")
                    meths=[]
                    for meth in tmp:
                        meths.append(meth.strip()) # get this guys method codes
    #
    # check if this is a pTRM check
    #
                    if float(rec["treatment_temp"])<float(rec_bak["treatment_temp"]): # went backward
                        if "LT-T-I" in meths and "LT-T-Z" in methbak:  #must be a pTRM check after first z
    #
    # replace LT-T-I method code with LT-PTRM-I
    #
                            methcodes=""
                            for meth in meths:
                                if meth!="LT-T-I":methcode=methcode+meth.strip()+":"
                            methcodes=methcodes+"LT-PTRM-I"
                            meths=methcodes.split(":")
                            pTRM=1
                        elif "LT-T-Z" in meths and "LT-T-I" in methbak:  # must be pTRM check after first I
    #
    # replace LT-T-Z method code with LT-PTRM-Z
    #
                            methcodes=""
                            for meth in meths:
                                if meth!="LT-T-Z":methcode=methcode+meth+":"
                            methcodes=methcodes+"LT-PTRM-Z"
                            meths=methcodes.split(":")
                            pTRM=1
                    methcodes=""
                    for meth in meths:
                        methcodes=methcodes+meth.strip()+":"
                    rec["magic_method_codes"]=methcodes[:-1]  #  attach new method code
                    rec_bak=rec # next previous record
                    tmp=rec_bak["magic_method_codes"].split(":")
                    methbak=[]
                    for meth in tmp:
                        methbak.append(meth.strip()) # previous steps method codes
    #
    # done with assigning pTRM checks.  data should be "fixed" in NewSpecs
    #
    # now let's find out which steps are infield zerofield (IZ) and which are zerofield infield (ZI)
    #
                rec_bak=NewSpecs[0]
                tmp=rec_bak["magic_method_codes"].split(":")
                methbak=[]
                for meth in tmp:
                    methbak.append(meth.strip()) # previous steps method codes
                if "LT-NO" not in methbak: # first measurement is not NRM
                    if "LT-T-I" in methbak: IZorZI="LP-PI-TRM-IZ" # first pair is IZ
                    if "LT-T-Z" in methbak: IZorZI="LP-PI-TRM-ZI" # first pair is ZI
                    if IZorZI not in methbak:methbak.append(IZorZI)
                    methcode=""
                    for meth in methbak:
                        methcode=methcode+meth+":"
                    NewSpecs[0]["magic_method_codes"]=methcode[:-1]  # fix first heating step when no NRM
                else: IZorZI="" # first measurement is NRM and not one of a pair
                for k in range(1,len(NewSpecs)): # hunt through measurements again
                    rec=NewSpecs[k]
                    tmp=rec["magic_method_codes"].split(":")
                    meths=[]
                    for meth in tmp:
                        meths.append(meth.strip()) # get this guys method codes
    #
    # check if this start a new temperature step of a infield/zerofield pair
    #
                    if float(rec["treatment_temp"])>float(rec_bak["treatment_temp"]) and "LT-PTRM-I" not in methbak: # new pair?
                        if "LT-T-I" in meths:  # infield of this pair
                                IZorZI="LP-PI-TRM-IZ"
                                IZ=1 # at least one IZ pair
                        elif "LT-T-Z" in meths: #zerofield
                                IZorZI="LP-PI-TRM-ZI"
                                ZI=1 # at least one ZI pair
                    elif float(rec["treatment_temp"])>float(rec_bak["treatment_temp"]) and "LT-PTRM-I" in methbak and IZorZI!="LP-PI-TRM-ZI": # new pair after out of sequence PTRM check?
                        if "LT-T-I" in meths:  # infield of this pair
                                IZorZI="LP-PI-TRM-IZ"
                                IZ=1 # at least one IZ pair
                        elif "LT-T-Z" in meths: #zerofield
                                IZorZI="LP-PI-TRM-ZI"
                                ZI=1 # at least one ZI pair
                    if float(rec["treatment_temp"])==float(rec_bak["treatment_temp"]): # stayed same temp
                        if "LT-T-Z" in meths and "LT-T-I" in methbak and IZorZI=="LP-PI-TRM-ZI":  #must be a tail check
    #
    # replace LT-T-Z method code with LT-PTRM-MD
    #
                            methcodes=""
                            for meth in meths:
                                if meth!="LT-T-Z":methcode=methcode+meth+":"
                            methcodes=methcodes+"LT-PTRM-MD"
                            meths=methcodes.split(":")
                            MD=1
    # fix method codes
                    if "LT-PTRM-I" not in meths and "LT-PTRM-MD" not in meths and IZorZI not in meths:meths.append(IZorZI)
                    newmeths=[]
                    for meth in meths:
                        if meth not in newmeths:newmeths.append(meth)  # try to get uniq set
                    methcode=""
                    for meth in newmeths:
                        methcode=methcode+meth+":"
                    rec["magic_method_codes"]=methcode[:-1]
                    rec_bak=rec # moving on to next record, making current one the backup
                    methbak=rec_bak["magic_method_codes"].split(":") # get last specimen's method codes in a list

    #
    # done with this specimen's records, now  check if any pTRM checks or MD checks
    #
                if pTRM==1:experiment_name=experiment_name+":LP-PI-ALT-PTRM"
                if MD==1:experiment_name=experiment_name+":LP-PI-BT-MD"
                if IZ==1 and ZI==1:experiment_name=experiment_name+":LP-PI-BT-IZZI"
                if IZ==1 and ZI==0:experiment_name=experiment_name+":LP-PI-IZ" # Aitken method
                if IZ==0 and ZI==1:experiment_name=experiment_name+":LP-PI-ZI" # Coe method
                IZ,ZI,pTRM,MD=0,0,0,0  # reset these for next specimen
                for rec in NewSpecs: # fix the experiment name for all recs for this specimen and save in SpecOuts
    # assign an experiment name to all specimen measurements from this specimen
                    if experiment_name!="":
                        rec["magic_method_codes"]=rec["magic_method_codes"]+":"+experiment_name
                    rec["magic_experiment_name"]=spec+":"+experiment_name
                    rec['measurement_number']='%i'%(measnum)  # assign measurement numbers
                    measnum+=1
                    SpecOuts.append(rec)
            elif experiment_name=="LP-PI-TRM:LP-PI-ALT-AFARM": # is a Shaw experiment!
                ARM,TRM=0,0
                for rec in NewSpecs: # fix the experiment name for all recs for this specimen and save in SpecOuts
    # assign an experiment name to all specimen measurements from this specimen
    # make the second ARM in Shaw experiments LT-AF-I-2, stick in the AF of ARM and TRM codes
                    meths=rec["magic_method_codes"].split(":")
                    if ARM==1:
                        if "LT-AF-I" in meths:
                            del meths[meths.index("LT-AF-I")]
                            meths.append("LT-AF-I-2")
                            ARM=2
                        if "LT-AF-Z" in meths and TRM==0 :
                            meths.append("LP-ARM-AFD")
                    if TRM==1 and ARM==1:
                        if "LT-AF-Z" in meths:
                            meths.append("LP-TRM-AFD")
                    if ARM==2:
                        if "LT-AF-Z" in meths:
                            meths.append("LP-ARM2-AFD")
                    newcode=""
                    for meth in meths:
                        newcode=newcode+meth+":"
                    rec["magic_method_codes"]=newcode[:-1]
                    if "LT-AF-I" in meths:ARM=1
                    if "LT-T-I" in meths:TRM=1
                    rec["magic_method_codes"]=rec["magic_method_codes"]+":"+experiment_name
                    rec["magic_experiment_name"]=spec+":"+experiment_name
                    rec['measurement_number']='%i'%(measnum)  # assign measurement numbers
                    measnum+=1
                    SpecOuts.append(rec)
            else:  # not a Thellier-Thellier  or a Shaw experiemnt
                for rec in  NewSpecs:
                    if experiment_name=="":
                        rec["magic_method_codes"]="LT-NO"
                        rec["magic_experiment_name"]=spec+":LT-NO"
                        rec['measurement_number']='%i'%(measnum)  # assign measurement numbers
                        measnum+=1
                    else:
                        if experiment_name not in rec['magic_method_codes']:
                            rec["magic_method_codes"]=rec["magic_method_codes"]+":"+experiment_name
                            rec["magic_method_codes"]=rec["magic_method_codes"].strip(':')
                        rec['measurement_number']='%i'%(measnum)  # assign measurement numbers
                        measnum+=1
                        rec["magic_experiment_name"]=spec+":"+experiment_name
                    rec["magic_software_packages"]=version_num
                    SpecOuts.append(rec)
        else:
            NewSpecs[0]["magic_experiment_name"]=spec+":"+NewSpecs[0]['magic_method_codes'].split(':')[0]
            NewSpecs[0]["magic_software_packages"]=version_num
            SpecOuts.append(NewSpecs[0]) # just copy over the single record as is
    return SpecOuts

def mw_measurements_methods(MagRecs):
# first collect all data for this specimen and do lab treatments
    MD,pMRM,IZ,ZI=0,0,0,0 # these are flags for the lab protocol codes
    expcodes=""
    NewSpecs,SpecMeths=[],[]
    experiment_name=""
    phi,theta="",""
    Dec,Inc="","" # NRM direction
    ZI,IZ,MD,pMRM="","","",""
    k=-1
    POWT_I,POWT_Z=[],[]
    ISteps,ZSteps=[],[]
    k=-1
    for rec in MagRecs:
        k+=1
# ready for pass through, step through specimens, check whether ptrm, ptrm tail checks, or AARM, etc.
#
#
# collect all the experimental data for this specimen
# and look through this specimen's records - try to figure out what experiment it is
#
        meths=rec["magic_method_codes"].split(":")
        powt=int(float(rec["treatment_mw_energy"]))
        for meth in meths:
            if meth not in SpecMeths:SpecMeths.append(meth)  # collect all the methods for this experiment
        if "LT-M-I" in meths: # infield step
            POWT_I.append(powt)
            ISteps.append(k)
            if phi=="": # first one
                phi=float(rec["treatment_dc_field_phi"])
                theta=float(rec["treatment_dc_field_theta"])
        if "LT-M-Z" in meths: # zero field  step
            POWT_Z.append(powt)
            ZSteps.append(k)
            if phi=="": # first one
                Dec=float(rec["measurement_dec"])
                Inc=float(rec["measurement_inc"])
    if "LT-M-I" not in  SpecMeths: # just microwave demag
        experiment_name="LP-DIR-M"
    else: # Microwave infield steps , some sort of LP-PI-M experiment
        experiment_name="LP-PI-M"
        if "LT-PMRM-Z"  in  SpecMeths or "LT-PMRM-I" in SpecMeths: # has pTRM checks
            experiment_name=experiment_name+":LP-PI-ALT-PMRM"
        if Dec!="" and phi!="":
            ang=angle([Dec,Inc],[phi,theta]) # angle between applied field and NRM
            if ang>= 0 and ang< 2: experiment_name=experiment_name+":LP-NRM-PAR"
            if ang> 88 and ang< 92: experiment_name=experiment_name+":LP-NRM-PERP"
            if ang> 178 and ang< 182: experiment_name=experiment_name+":LP-NRM-APAR"
#
# now check whether there are z pairs for all I steps or is this a single heating experiment
#
        noZ=0
        for powt in POWT_I:
            if powt not in POWT_Z:noZ=1 # some I's missing their Z's
        if noZ==1:
            meths = experiment_name.split(":")
            if  "LP-NRM-PERP" in meths: # this is a single  heating experiment
                experiment_name=experiment_name+":LP-PI-M-S"
            else:
                print "Trouble interpreting file - missing zerofield steps? "
                sys.exit()
        else: # this is a double heating experiment
            experiment_name=experiment_name+":LP-PI-M-D"
  # check for IZ or ZI pairs
            for  istep in ISteps: # look for first zerofield step with this power
                rec=MagRecs[istep]
                powt_i=int(float(rec["treatment_mw_energy"]))
                IZorZI,step="",-1
                while IZorZI =="" and step<len(ZSteps)-1:
                    step+=1
                    zstep=ZSteps[step]
                    zrec=MagRecs[zstep]
                    powt_z=int(float(zrec["treatment_mw_energy"]))
                    if powt_i==powt_z:  # found a match
                        if zstep < istep: # zero field first
                            IZorZI="LP-PI-M-ZI"
                            ZI=1 # there is at least one ZI step
                            break
                        else: # in field first
                            IZorZI="LP-PI-M-IZ"
                            IZ=1 # there is at least one ZI step
                            break
                if IZorZI!="":
                    MagRecs[istep]['magic_method_codes']= MagRecs[istep]['magic_method_codes']+':'+IZorZI
                    MagRecs[zstep]['magic_method_codes']= MagRecs[zstep]['magic_method_codes']+':'+IZorZI
            print POWT_Z
            print POWT_I
            for  istep in ISteps: # now look for MD checks (zero field)
              if istep+2<len(MagRecs):  # only if there is another step to consider
                irec=MagRecs[istep]
                powt_i=int(float(irec["treatment_mw_energy"]))
                print istep,powt_i,ZSteps[POWT_Z.index(powt_i)]
                if powt_i in POWT_Z and ZSteps[POWT_Z.index(powt_i)] < istep:  # if there is a previous zero field step at same  power
                    nrec=MagRecs[istep+1] # next step
                    nmeths=nrec['magic_method_codes'].split(":")
                    powt_n=int(float(nrec["treatment_mw_energy"]))
                    if 'LT-M-Z' in nmeths and powt_n==powt_i:  # the step after this infield was a zero field at same energy
                        MD=1  # found a second zero field  match
                        mdmeths=MagRecs[istep+1]['magic_method_codes'].split(":")
                        mdmeths[0]="LT-PMRM-MD" # replace method code with tail check code
                        methods=""
                        for meth in mdmeths:methods=methods+":"+meth
                        MagRecs[istep+1]['magic_method_codes']=methods[1:]
            if MD==1: experiment_name=experiment_name+":LP-PI-BT-MD"
            if IZ==1:
                if ZI==1:
                    experiment_name=experiment_name+":LP-PI-BT-IZZI"
                else:
                    experiment_name=experiment_name+":LP-PI-M-IZ"
            else:
                if ZI==1:
                    experiment_name=experiment_name+":LP-PI-M-ZI"
                else:
                    print "problem in measurements_methods - no ZI or IZ in double heating experiment"
                    sys.exit()
    for rec in MagRecs:
        if 'er_synthetic_name' in rec.keys() and rec['er_synthetic_name']!="":
            rec['magic_experiment_name']=rec['er_synthetic_name']+":"+experiment_name
        else:
            rec['magic_experiment_name']=rec['er_specimen_name']+":"+experiment_name
        rec['magic_method_codes']=rec['magic_method_codes']+":"+experiment_name
    return MagRecs

def parse_site(sample,convention,Z):
    """
    parse the site name from the sample name using the specified convention
    """
    site=sample # default is that site = sample
#
#
# Sample is final letter on site designation eg:  TG001a (used by SIO lab in San Diego)
    if convention=="1":
        return sample[:-1] # peel off terminal character
#
# Site-Sample format eg:  BG94-1  (used by PGL lab in Beijing)
#
    if convention=="2":
        parts=sample.strip('-').split('-')
        return parts[0]
#
# Sample is XXXX.YY where XXX is site and YY is sample
#
    if convention=="3":
        parts=sample.split('.')
        return parts[0]
#
# Sample is XXXXYYY where XXX is site desgnation and YYY is Z long integer
#
    if convention=="4":
       k=int(Z)-1
       return sample[0:-k]  # peel off Z characters from site

    if convention=="5": # sample == site
        return sample

    if convention=="7": # peel off Z characters for site
       k=int(Z)
       return sample[0:k]

    if convention=="8": # peel off Z characters for site
       return ""
    if convention=="9": # peel off Z characters for site
       return sample

    print "Error in site parsing routine"
    sys.exit()
def get_samp_con():
    """
     get sample naming  convention
    """
#
    samp_con,Z="",""
    while samp_con=="":
        samp_con=raw_input("""
        Sample naming convention:
            [1] XXXXY: where XXXX is an arbitrary length site designation and Y
                is the single character sample designation.  e.g., TG001a is the
                first sample from site TG001.  	 [default]
            [2] XXXX-YY: YY sample from site XXXX (XXX, YY of arbitary length)
            [3] XXXX.YY: YY sample from site XXXX (XXX, YY of arbitary length)
            [4-Z] XXXX[YYY]:  YYY is sample designation with Z characters from site XXX
            [5] site name same as sample
            [6] site is entered under a separate column
            [7-Z] [XXXX]YYY:  XXXX is site designation with Z characters with sample name XXXXYYYY
            NB: all others you will have to customize your self
                 or e-mail ltauxe@ucsd.edu for help.
            select one:
""")
    #
        if samp_con=="" or  samp_con =="1":
            samp_con,Z="1",1
        if "4" in samp_con:
            if "-" not in samp_con:
                print "option [4] must be in form 4-Z where Z is an integer"
                samp_con=""
            else:
                Z=samp_con.split("-")[1]
                samp_con="4"
        if "7" in samp_con:
            if "-" not in samp_con:
                print "option [7] must be in form 7-Z where Z is an integer"
                samp_con=""
            else:
                Z=samp_con.split("-")[1]
                samp_con="7"
        if samp_con.isdigit()==False or int(samp_con)>7:
            print "Try again\n "
            samp_con=""
    return samp_con,Z

def get_tilt(dec_geo,inc_geo,dec_tilt,inc_tilt):
#
    """
    Function to return dip and dip direction used to convert geo to tilt coordinates
    """
# strike is horizontal line equidistant from two input directions
    SCart=[0,0,0] # cartesian coordites of Strike
    SCart[2]=0.  # by definition
    GCart=dir2cart([dec_geo,inc_geo,1.]) # cartesian coordites of Geographic D
    TCart=dir2cart([dec_tilt,inc_tilt,1.]) # cartesian coordites of Tilt D
    X=(TCart[1]-GCart[1])/(GCart[0]-TCart[0])
    SCart[1]=numpy.sqrt(1/(X**2+1.))
    SCart[0]=SCart[1]*X
    SDir=cart2dir(SCart)
    DipDir=(SDir[0]+90.)%360.
# D is creat circle distance between geo direction and strike
# theta is GCD between geo and tilt (on unit sphere).  use law of cosines
# to get small cirlce between geo and tilt (dip)
    cosd = GCart[0]*SCart[0]+GCart[1]*SCart[1]  # cosine of angle between two
    d=numpy.arccos(cosd)
    cosTheta=GCart[0]*TCart[0]+GCart[1]*TCart[1]+GCart[2]*TCart[2]
    Dip =(180./numpy.pi)*numpy.arccos(-((cosd**2-cosTheta)/numpy.sin(d)**2))
    return DipDir,Dip
#
def get_azpl(cdec,cinc,gdec,ginc):
    """
     gets azimuth and pl from specimen dec inc (cdec,cinc) and gdec,ginc (geographic)  coordinates
    """
    TOL=1e-4
    rad=numpy.pi/180.
    Xp=dir2cart([gdec,ginc,1.])
    X=dir2cart([cdec,cinc,1.])
    # find plunge first
    az,pl,zdif,ang=0.,-90.,1.,360.
    while  zdif>TOL and pl<180.:
        znew=X[0]*numpy.sin(pl*rad)+X[2]*numpy.cos(pl*rad)
        zdif=abs(Xp[2]-znew)
        pl+=.01

    while ang>0.1 and az<360.:
        d,i=dogeo(cdec,cinc,az,pl)
        ang=angle([gdec,ginc],[d,i])
        az+=.01
    return az-.01,pl-.01

def set_priorities(SO_methods,ask):
    """
     figure out which sample_azimuth to use, if multiple orientation methods
    """
    # if ask set to 1, then can change priorities
    SO_defaults=['SO-SUN','SO-GPS-DIFF','SO-SIGHT','SO-SIGHT-BS','SO-CMD-NORTH','SO-MAG','SO-SM','SO-REC','SO-V','SO-CORE','SO-NO']
    SO_priorities,prior_list=[],[]
    if len(SO_methods) >= 1:
        for l in range(len(SO_defaults)):
            if SO_defaults[l] in SO_methods:
                SO_priorities.append(SO_defaults[l])
    pri,change=0,"1"
    if ask==1:
        print  """These methods of sample orientation were found:
      They have been assigned a provisional priority (top = zero, last = highest number) """
        for m in range(len(SO_defaults)):
            if SO_defaults[m] in SO_methods:
                SO_priorities[SO_methods.index(SO_defaults[m])]=pri
                pri+=1
        while change=="1":
            prior_list=SO_priorities
            for m in range(len(SO_methods)):
                print SO_methods[m],SO_priorities[m]
            change=raw_input("Change these?  1/[0] ")
            if change!="1":break
        SO_priorities=[]
        for l in range(len(SO_methods)):
             print SO_methods[l]
             print " Priority?   ",prior_list
             pri=int(raw_input())
             SO_priorities.append(pri)
             del prior_list[prior_list.index(pri)]
    return SO_priorities
#
#
def get_EOL(file):
    """
     find EOL of input file (whether mac,PC or unix format)
    """
    f=open(file,'r')
    firstline=f.read(350)
    EOL=""
    for k in range(350):
        if firstline[k:k+2] == "\r\n":
            print file, ' appears to be a dos file'
            EOL='\r\n'
            break
    if EOL=="":
        for k in range(350):
            if firstline[k] == "\r":
                print file, ' appears to be a mac file'
                EOL='\r'
    if EOL=="":
        print file, " appears to be a  unix file"
        EOL='\n'
    f.close()
    return EOL
#
def sortshaw(s,datablock):
    """
     sorts data block in to ARM1,ARM2 NRM,TRM,ARM1,ARM2=[],[],[],[]
     stick  first zero field stuff into first_Z
    """
    for rec in datablock:
        methcodes=rec["magic_method_codes"].split(":")
        step=float(rec["treatment_ac_field"])
        str=float(rec["measurement_magn_moment"])
        if "LT-NO" in methcodes:
            NRM.append([0,str])
        if "LT-T-I" in methcodes:
            TRM.append([0,str])
            field=float(rec["treatment_dc_field"])
        if "LT-AF-I" in methcodes:
            ARM1.append([0,str])
        if "LT-AF-I-2" in methcodes:
            ARM2.append([0,str])
        if "LT-AF-Z" in methcodes:
            if "LP-ARM-AFD" in methcodes:
                ARM1.append([step,str])
            elif "LP-TRM-AFD" in methcodes:
                TRM.append([step,str])
            elif "LP-ARM2-AFD" in methcodes:
                ARM2.append([step,str])
            else:
                NRM.append([step,str])
    cont=1
    while cont==1:
        if len(NRM)!=len(TRM):
            print "Uneven NRM/TRM steps: "
            NRM,TRM,cont=cleanup(TRM,NRM)
        else:cont=0
    cont=1
    while cont==1:
        if len(ARM1)!=len(ARM2):
            print "Uneven ARM1/ARM2 steps: "
            ARM1,ARM2,cont=cleanup(ARM2,ARM1)
        else:cont=0
#
# final check
#
    if len(NRM)!=len(TRM) or len(ARM1)!=len(ARM2):
               print len(NRM),len(TRM),len(ARM1),len(ARM2)
               print " Something wrong with this specimen! Better fix it or delete it "
               raw_input(" press return to acknowledge message")
# now do the ratio to "fix" NRM/TRM data
# a
    TRM_ADJ=[]
    for kk in range(len(TRM)):
        step=TRM[kk][0]
        for k in range(len(ARM1)):
            if  ARM1[k][0]==step:
                TRM_ADJ.append([step,TRM[kk][1]*ARM1[k][1]/ARM2[k][1]])
                break
    shawblock=(NRM,TRM,ARM1,ARM2,TRM_ADJ)
    return shawblock,field
#
#
def makelist(List):
    """
     makes a colon delimited list from List
    """
    clist=""
    for element in List:
        clist=clist+element+":"
    return clist[:-1]
#
def getvec(gh,lat,long):
#
    """
       evaluates the vector at a given latitude (long=0) for a specified set of coefficients
        Lisa Tauxe 2/26/2007
    """

#
#
    sv=[]
    pad=120-len(gh)
    for x in range(pad):gh.append(0.)
    for x in range(len(gh)):sv.append(0.)
#! convert to colatitude for MB routine
    itype = 1
    colat = 90.-lat
    date,alt=2000.,0. # use a dummy date and altitude
    x,y,z,f=magsyn(gh,sv,date,date,itype,alt,colat,long)
    vec=cart2dir([x,y,z])
    vec[2]=f
    return vec
#
def s_l(l,alpha):
    """
    get sigma as a function of degree l from Constable and Parker (1988)
    """
    a2=alpha**2
    c_a=0.547
    s_l=numpy.sqrt(((c_a**(2.*l))*a2)/((l+1.)*(2.*l+1.)))
    return s_l
#
def mktk03(terms,seed,G2,G3):
    """
    generates a list of gauss coefficients drawn from the TK03.gad distribution
    """
#random.seed(n)
    p=0
    n=seed
    gh=[]
    g10,sfact,afact=-18e3,3.8,2.4
    g20=G2*g10
    g30=G3*g10
    alpha=g10/afact
    s1=s_l(1,alpha)
    s10=sfact*s1
    gnew=random.normal(g10,s10)
    if p==1:print 1,0,gnew,0
    gh.append(gnew)
    gh.append(random.normal(0,s1))
    gnew=gh[-1]
    gh.append(random.normal(0,s1))
    hnew=gh[-1]
    if p==1:print 1,1,gnew,hnew
    for l in range(2,terms+1):
        for m in range(l+1):
            OFF=0.0
            if l==2 and m==0:OFF=g20
            if l==3 and m==0:OFF=g30
            s=s_l(l,alpha)
            j=(l-m)%2
            if j==1:
                s=s*sfact
            gh.append(random.normal(OFF,s))
            gnew=gh[-1]
            if m==0:
                hnew=0
            else:
                gh.append(random.normal(0,s))
                hnew=gh[-1]
            if p==1:print l,m,gnew,hnew
    return gh
#
#
def pinc(lat):
    """
    calculate paleoinclination from latitude
    """
    rad = numpy.pi/180.
    tanl=numpy.tan(lat*rad)
    inc=numpy.arctan(2.*tanl)
    return inc/rad
#
def plat(inc):
    """
    calculate paleolat from inclination
    """
    rad = numpy.pi/180.
    tani=numpy.tan(inc*rad)
    lat=numpy.arctan(tani/2.)
    return lat/rad
#
#
def pseudo(DIs):
    """
     draw a bootstrap sample of Directions
    """
#
    Inds=numpy.random.randint(len(DIs),size=len(DIs))
    D=numpy.array(DIs)
    return D[Inds]
#
def di_boot(DIs):
    """
     returns bootstrap parameters for Directional data
    """
# get average DI for whole dataset
    fpars=fisher_mean(DIs)
#
# now do bootstrap to collect BDIs  bootstrap means
#
    nb,BDIs=5000,[]  # number of bootstraps, list of bootstrap directions
#

    for k in range(nb): # repeat nb times
#        if k%50==0:print k,' out of ',nb
        pDIs= pseudo(DIs) # get a pseudosample
        bfpars=fisher_mean(pDIs) # get bootstrap mean bootstrap sample
        BDIs.append([bfpars['dec'],bfpars['inc']])
    return BDIs

def pseudosample(x):
    """
     draw a bootstrap sample of x
    """
#
    BXs=[]
    for k in range(len(x)):
        ind=random.randint(0,len(x)-1)
        BXs.append(x[ind])
    return BXs

def get_plate_data(plate):
    """
    returns the pole list for a given plate
    """
    if plate=='AF':
       apwp="""
0.0        90.00    0.00
1.0        88.38  182.20
2.0        86.76  182.20
3.0        86.24  177.38
4.0        86.08  176.09
5.0        85.95  175.25
6.0        85.81  174.47
7.0        85.67  173.73
8.0        85.54  173.04
9.0        85.40  172.39
10.0       85.26  171.77
11.0       85.12  171.19
12.0       84.97  170.71
13.0       84.70  170.78
14.0       84.42  170.85
15.0       84.10  170.60
16.0       83.58  169.22
17.0       83.06  168.05
18.0       82.54  167.05
19.0       82.02  166.17
20.0       81.83  166.63
21.0       82.13  169.10
22.0       82.43  171.75
23.0       82.70  174.61
24.0       82.96  177.69
25.0       83.19  180.98
26.0       83.40  184.50
27.0       82.49  192.38
28.0       81.47  198.49
29.0       80.38  203.25
30.0       79.23  207.04
31.0       78.99  206.32
32.0       78.96  204.60
33.0       78.93  202.89
34.0       78.82  201.05
35.0       78.54  198.97
36.0       78.25  196.99
37.0       77.95  195.10
38.0       77.63  193.30
39.0       77.30  191.60
40.0       77.56  192.66
41.0       77.81  193.77
42.0       78.06  194.92
43.0       78.31  196.13
44.0       78.55  197.38
45.0       78.78  198.68
46.0       79.01  200.04
47.0       79.03  201.22
48.0       78.92  202.23
49.0       78.81  203.22
50.0       78.67  204.34
51.0       78.30  206.68
52.0       77.93  208.88
53.0       77.53  210.94
54.0       77.12  212.88
55.0       76.70  214.70
56.0       76.24  216.60
57.0       75.76  218.37
58.0       75.27  220.03
59.0       74.77  221.58
60.0       74.26  223.03
61.0       73.71  225.04
62.0       73.06  228.34
63.0       72.35  231.38
64.0       71.60  234.20
65.0       71.49  234.96
66.0       71.37  235.71
67.0       71.26  236.45
68.0       71.14  237.18
69.0       71.24  236.94
70.0       71.45  236.27
71.0       71.65  235.59
72.0       71.85  234.89
73.0       72.04  234.17
74.0       72.23  233.45
75.0       72.42  232.70
76.0       71.97  236.12
77.0       70.94  241.83
78.0       69.76  246.94
79.0       68.44  251.48
80.0       68.01  252.16
81.0       67.68  252.45
82.0       67.36  252.72
83.0       67.03  252.99
84.0       66.91  252.32
85.0       66.91  251.01
86.0       66.91  249.71
87.0       66.89  248.40
88.0       66.87  247.10
89.0       66.83  245.80
90.0       66.78  244.50
91.0       66.73  243.21
92.0       66.66  243.44
93.0       66.59  244.66
94.0       66.51  245.88
95.0       66.86  247.10
96.0       67.26  248.35
97.0       67.64  249.65
98.0       68.02  250.99
99.0       68.38  252.38
100.0      68.73  253.81
101.0      67.73  253.53
102.0      66.39  252.89
103.0      65.05  252.31
104.0      63.71  251.79
105.0      62.61  252.26
106.0      61.86  254.08
107.0      61.10  255.82
108.0      60.31  257.47
109.0      59.50  259.05
110.0      58.67  260.55
111.0      57.94  261.67
112.0      57.64  261.52
113.0      57.33  261.38
114.0      57.03  261.23
115.0      56.73  261.09
116.0      56.42  260.95
117.0      55.57  260.90
118.0      54.35  260.90
119.0      53.14  260.90
120.0      51.92  260.90
121.0      51.40  260.83
122.0      50.96  260.76
123.0      50.58  260.83
124.0      50.45  261.47
125.0      50.32  262.11
126.0      50.19  262.74
127.0      50.06  263.37
128.0      49.92  264.00
129.0      49.78  264.62
130.0      49.63  265.25
131.0      49.50  265.76
132.0      49.50  265.41
133.0      49.50  265.06
134.0      49.50  264.71
135.0      48.67  264.80
136.0      47.50  265.07
137.0      46.32  265.34
138.0      45.14  265.59
139.0      43.95  265.83
140.0      42.75  265.17
141.0      41.53  264.17
142.0      40.30  263.20
143.0      41.89  262.76
144.0      43.49  262.29
145.0      45.08  261.80
146.0      46.67  261.29
147.0      48.25  260.74
148.0      49.84  260.15
149.0      51.42  259.53
150.0      52.99  258.86
151.0      54.57  258.14
152.0      56.14  257.37
153.0      57.70  256.52
154.0      59.05  255.88
155.0      58.56  257.68
156.0      57.79  258.80
157.0      56.41  258.47
158.0      55.04  258.16
159.0      53.78  257.93
160.0      53.60  258.23
161.0      53.41  258.52
162.0      53.23  258.81
163.0      53.04  259.10
164.0      52.85  259.38
165.0      52.67  259.67
166.0      52.48  259.95
167.0      52.29  260.22
168.0      52.10  260.50
169.0      54.10  259.90
170.0      56.10  259.24
171.0      57.63  259.26
172.0      59.05  259.48
173.0      60.47  259.71
174.0      61.88  259.97
175.0      63.30  260.25
176.0      64.71  260.56
177.0      65.90  261.33
178.0      66.55  263.15
179.0      67.21  263.56
180.0      67.88  262.97
181.0      68.56  262.34
182.0      69.23  261.68
183.0      69.06  261.18
184.0      68.32  260.84
185.0      67.58  260.53
186.0      66.84  260.23
187.0      66.09  259.95
188.0      65.35  259.68
189.0      64.61  259.43
190.0      63.87  259.19
191.0      63.12  258.97
192.0      62.63  258.67
193.0      62.24  258.34
194.0      61.86  258.02
195.0      62.06  256.25
196.0      62.62  253.40
197.0      63.13  250.46
198.0      63.56  247.41
"""
    if plate=='ANT':
       apwp="""
0.0        90.00    0.00
1.0        88.48  178.80
2.0        86.95  178.80
3.0        86.53  172.26
4.0        86.46  169.30
5.0        86.41  166.81
6.0        86.35  164.39
7.0        86.29  162.05
8.0        86.22  159.79
9.0        86.15  157.62
10.0       86.07  155.53
11.0       85.98  153.53
12.0       85.88  151.77
13.0       85.63  151.47
14.0       85.39  151.20
15.0       85.10  150.74
16.0       84.60  149.57
17.0       84.10  148.60
18.0       83.60  147.78
19.0       83.10  147.07
20.0       82.99  146.90
21.0       83.46  147.46
22.0       83.93  148.10
23.0       84.40  148.85
24.0       84.87  149.74
25.0       85.34  150.80
26.0       85.80  152.10
27.0       85.57  166.36
28.0       85.09  178.53
29.0       84.44  188.22
30.0       83.67  195.72
31.0       83.55  194.37
32.0       83.58  191.03
33.0       83.60  187.66
34.0       83.52  184.03
35.0       83.23  180.01
36.0       82.91  176.34
37.0       82.56  172.99
38.0       82.19  169.96
39.0       81.80  167.20
40.0       82.22  166.10
41.0       82.64  164.87
42.0       83.05  163.49
43.0       83.46  161.94
44.0       83.86  160.19
45.0       84.26  158.20
46.0       84.65  155.91
47.0       84.85  155.14
48.0       84.94  155.56
49.0       85.02  156.00
50.0       85.11  156.86
51.0       85.22  161.60
52.0       85.29  166.52
53.0       85.33  171.57
54.0       85.33  176.65
55.0       85.30  181.70
56.0       85.23  187.68
57.0       85.11  193.43
58.0       84.94  198.85
59.0       84.74  203.89
60.0       84.49  208.51
61.0       84.23  214.70
62.0       83.87  224.68
63.0       83.35  233.34
64.0       82.70  240.60
65.0       82.75  243.15
66.0       82.78  245.72
67.0       82.80  248.32
68.0       82.80  250.92
69.0       83.19  251.41
70.0       83.74  250.94
71.0       84.29  250.38
72.0       84.84  249.70
73.0       85.39  248.86
74.0       85.94  247.79
75.0       86.48  246.39
76.0       86.07  261.42
77.0       84.60  277.45
78.0       82.89  286.25
79.0       81.08  291.58
80.0       80.93  293.29
81.0       80.96  294.72
82.0       80.98  296.17
83.0       81.00  297.62
84.0       81.51  298.75
85.0       82.37  299.83
86.0       83.22  301.18
87.0       84.06  302.91
88.0       84.90  305.21
89.0       85.73  308.41
90.0       86.54  313.11
91.0       87.31  320.59
92.0       87.40  334.40
93.0       86.93  346.81
94.0       86.36  355.67
95.0       85.61    7.48
96.0       84.70   16.06
97.0       83.71   22.06
98.0       82.68   26.39
99.0       81.61   29.65
100.0      80.52   32.16
101.0      80.70   31.28
102.0      81.18   29.47
103.0      81.66   27.45
104.0      82.13   25.19
105.0      82.14   22.30
106.0      81.49   19.18
107.0      80.81   16.51
108.0      80.11   14.20
109.0      79.40   12.20
110.0      78.68   10.45
111.0      78.05    9.62
112.0      77.79   11.65
113.0      77.52   13.60
114.0      77.23   15.46
115.0      76.94   17.24
116.0      76.63   18.94
117.0      76.60   18.39
118.0      76.74   16.34
119.0      76.88   14.25
120.0      76.99   12.12
121.0      76.94   12.67
122.0      76.86   13.53
123.0      76.68   14.35
124.0      76.08   15.08
125.0      75.48   15.75
126.0      74.88   16.36
127.0      74.27   16.93
128.0      73.66   17.46
129.0      73.06   17.95
130.0      72.45   18.41
131.0      71.90   18.79
132.0      71.87   18.70
133.0      71.84   18.61
134.0      71.81   18.53
135.0      71.81   15.55
136.0      71.74   11.34
137.0      71.59    7.18
138.0      71.34    3.11
139.0      71.01  359.16
140.0      71.25  355.22
141.0      71.67  351.10
142.0      72.00  346.80
143.0      72.09  352.56
144.0      72.01  358.32
145.0      71.77    3.99
146.0      71.36    9.46
147.0      70.80   14.67
148.0      70.10   19.55
149.0      69.28   24.10
150.0      68.35   28.28
151.0      67.32   32.13
152.0      66.21   35.64
153.0      65.02   38.85
154.0      63.85   41.25
155.0      63.30   38.84
156.0      63.13   36.67
157.0      63.86   34.84
158.0      64.58   32.92
159.0      65.17   31.04
160.0      64.92   30.50
161.0      64.66   29.97
162.0      64.40   29.44
163.0      64.14   28.93
164.0      63.87   28.43
165.0      63.61   27.93
166.0      63.34   27.44
167.0      63.07   26.97
168.0      62.80   26.50
169.0      61.86   30.42
170.0      60.82   34.09
171.0      59.74   36.31
172.0      58.64   38.08
173.0      57.52   39.75
174.0      56.37   41.31
175.0      55.21   42.78
176.0      54.03   44.17
177.0      52.92   45.01
178.0      51.98   44.71
179.0      51.38   45.20
180.0      51.02   46.19
181.0      50.64   47.16
182.0      50.26   48.12
183.0      50.50   48.18
184.0      51.16   47.63
185.0      51.82   47.07
186.0      52.47   46.49
187.0      53.13   45.89
188.0      53.78   45.28
189.0      54.43   44.64
190.0      55.07   43.98
191.0      55.71   43.31
192.0      56.19   42.92
193.0      56.61   42.67
194.0      57.03   42.41
195.0      57.37   43.88
196.0      57.62   46.54
197.0      57.80   49.23
198.0      57.93   51.94
"""
    if plate=='AU':
       apwp="""
0.0        90.00    0.00
1.0        88.81  204.00
2.0        87.62  204.00
3.0        87.50  207.24
4.0        87.58  216.94
5.0        87.58  227.69
6.0        87.51  238.13
7.0        87.35  247.65
8.0        87.14  255.93
9.0        86.87  262.92
10.0       86.56  268.74
11.0       86.22  273.56
12.0       85.87  277.29
13.0       85.52  278.11
14.0       85.18  278.81
15.0       84.87  279.00
16.0       84.71  277.55
17.0       84.54  276.18
18.0       84.37  274.90
19.0       84.20  273.69
20.0       83.80  275.43
21.0       83.01  280.56
22.0       82.18  284.64
23.0       81.31  287.92
24.0       80.42  290.60
25.0       79.52  292.83
26.0       78.60  294.70
27.0       77.32  290.94
28.0       76.00  287.87
29.0       74.65  285.33
30.0       73.28  283.19
31.0       72.98  283.37
32.0       72.95  284.09
33.0       72.92  284.80
34.0       72.92  285.21
35.0       72.97  284.91
36.0       73.03  284.61
37.0       73.09  284.31
38.0       73.14  284.01
39.0       73.20  283.70
40.0       72.83  285.38
41.0       72.45  286.99
42.0       72.06  288.54
43.0       71.65  290.02
44.0       71.24  291.44
45.0       70.81  292.80
46.0       70.38  294.10
47.0       70.08  294.79
48.0       69.88  295.11
49.0       69.68  295.42
50.0       69.46  295.67
51.0       69.01  295.35
52.0       68.55  295.05
53.0       68.10  294.75
54.0       67.65  294.47
55.0       67.20  294.20
56.0       66.69  293.91
57.0       66.18  293.63
58.0       65.68  293.37
59.0       65.17  293.11
60.0       64.66  292.87
61.0       63.96  292.74
62.0       62.84  292.87
63.0       61.72  292.99
64.0       60.60  293.10
65.0       60.35  293.65
66.0       60.09  294.19
67.0       59.84  294.72
68.0       59.58  295.24
69.0       59.76  295.88
70.0       60.14  296.57
71.0       60.51  297.28
72.0       60.88  298.00
73.0       61.24  298.75
74.0       61.60  299.51
75.0       61.96  300.28
76.0       60.92  301.16
77.0       58.95  302.00
78.0       56.98  302.76
79.0       55.00  303.44
80.0       54.72  303.90
81.0       54.63  304.34
82.0       54.53  304.79
83.0       54.44  305.22
84.0       54.82  305.66
85.0       55.51  306.11
86.0       56.20  306.57
87.0       56.89  307.05
88.0       57.58  307.55
89.0       58.26  308.07
90.0       58.95  308.61
91.0       59.63  309.17
92.0       59.80  310.34
93.0       59.62  311.90
94.0       59.42  313.45
95.0       59.46  315.65
96.0       59.50  317.94
97.0       59.49  320.23
98.0       59.44  322.51
99.0       59.36  324.79
100.0      59.23  327.05
101.0      59.10  326.62
102.0      58.98  325.52
103.0      58.84  324.43
104.0      58.69  323.34
105.0      58.29  322.95
106.0      57.53  323.57
107.0      56.75  324.16
108.0      55.98  324.73
109.0      55.20  325.27
110.0      54.42  325.80
111.0      53.81  326.35
112.0      53.88  327.12
113.0      53.94  327.88
114.0      53.99  328.65
115.0      54.04  329.42
116.0      54.08  330.19
117.0      53.91  330.07
118.0      53.59  329.36
119.0      53.26  328.66
120.0      52.93  327.97
121.0      52.97  328.13
122.0      53.04  328.39
123.0      53.03  328.78
124.0      52.70  329.69
125.0      52.35  330.59
126.0      52.00  331.47
127.0      51.65  332.34
128.0      51.29  333.20
129.0      50.92  334.04
130.0      50.54  334.87
131.0      50.18  335.59
132.0      50.01  335.53
133.0      49.83  335.48
134.0      49.65  335.42
135.0      48.86  334.35
136.0      47.78  332.89
137.0      46.68  331.50
138.0      45.57  330.16
139.0      44.44  328.88
140.0      43.86  327.11
141.0      43.50  325.14
142.0      43.10  323.20
143.0      44.00  325.32
144.0      44.85  327.50
145.0      45.66  329.75
146.0      46.43  332.06
147.0      47.15  334.44
148.0      47.81  336.88
149.0      48.43  339.38
150.0      48.99  341.94
151.0      49.49  344.55
152.0      49.93  347.22
153.0      50.31  349.93
154.0      50.48  352.37
155.0      49.32  352.03
156.0      48.45  351.31
157.0      48.28  349.67
158.0      48.09  348.05
159.0      47.87  346.61
160.0      47.53  346.69
161.0      47.19  346.77
162.0      46.84  346.85
163.0      46.50  346.93
164.0      46.16  347.00
165.0      45.82  347.08
166.0      45.48  347.15
167.0      45.14  347.23
168.0      44.80  347.30
169.0      45.48  349.99
170.0      46.09  352.74
171.0      46.20  354.95
172.0      46.16  357.01
173.0      46.09  359.07
174.0      45.98    1.12
175.0      45.83    3.16
176.0      45.65    5.19
177.0      45.27    6.85
178.0      44.51    7.68
179.0      44.31    8.58
180.0      44.50    9.55
181.0      44.67   10.52
182.0      44.84   11.51
183.0      45.02   11.29
184.0      45.22   10.27
185.0      45.42    9.24
186.0      45.60    8.20
187.0      45.77    7.16
188.0      45.93    6.11
189.0      46.09    5.05
190.0      46.23    3.99
191.0      46.36    2.92
192.0      46.52    2.20
193.0      46.68    1.62
194.0      46.84    1.03
195.0      47.67    1.40
196.0      48.95    2.45
197.0      50.22    3.54
198.0      51.48    4.70
"""
    if plate=='EU':
       apwp="""
0.0        90.00    0.00
1.0        88.43  178.70
2.0        86.86  178.70
3.0        86.34  172.60
4.0        86.18  169.84
5.0        86.05  167.60
6.0        85.91  165.51
7.0        85.77  163.55
8.0        85.62  161.73
9.0        85.46  160.03
10.0       85.31  158.44
11.0       85.15  156.95
12.0       84.97  155.67
13.0       84.70  155.37
14.0       84.42  155.10
15.0       84.08  154.59
16.0       83.51  153.18
17.0       82.92  152.01
18.0       82.34  151.01
19.0       81.75  150.16
20.0       81.55  149.86
21.0       81.93  150.29
22.0       82.30  150.76
23.0       82.68  151.28
24.0       83.05  151.85
25.0       83.43  152.49
26.0       83.80  153.20
27.0       83.47  162.05
28.0       83.00  169.89
29.0       82.41  176.64
30.0       81.74  182.37
31.0       81.53  181.04
32.0       81.43  178.14
33.0       81.30  175.32
34.0       81.08  172.47
35.0       80.66  169.55
36.0       80.22  166.89
37.0       79.76  164.46
38.0       79.29  162.23
39.0       78.80  160.20
40.0       79.13  159.12
41.0       79.45  157.97
42.0       79.77  156.75
43.0       80.08  155.46
44.0       80.39  154.08
45.0       80.69  152.62
46.0       80.98  151.05
47.0       81.13  150.65
48.0       81.19  151.08
49.0       81.25  151.51
50.0       81.31  152.21
51.0       81.38  155.38
52.0       81.43  158.60
53.0       81.44  161.83
54.0       81.44  165.08
55.0       81.40  168.30
56.0       81.33  172.18
57.0       81.22  175.97
58.0       81.07  179.66
59.0       80.89  183.21
60.0       80.67  186.61
61.0       80.49  190.87
62.0       80.37  197.35
63.0       80.14  203.60
64.0       79.80  209.50
65.0       79.85  210.35
66.0       79.90  211.20
67.0       79.94  212.07
68.0       79.99  212.94
69.0       80.20  211.11
70.0       80.46  207.98
71.0       80.69  204.68
72.0       80.89  201.23
73.0       81.05  197.65
74.0       81.18  193.94
75.0       81.27  190.14
76.0       81.59  195.53
77.0       81.79  207.82
78.0       81.61  220.13
79.0       81.07  231.45
80.0       81.02  232.09
81.0       81.05  231.62
82.0       81.07  231.16
83.0       81.09  230.69
84.0       81.26  227.31
85.0       81.47  221.76
86.0       81.59  216.00
87.0       81.63  210.12
88.0       81.58  204.25
89.0       81.45  198.51
90.0       81.23  192.99
91.0       80.94  187.78
92.0       81.02  185.31
93.0       81.39  184.44
94.0       81.76  183.50
95.0       82.43  179.95
96.0       83.10  175.40
97.0       83.71  169.92
98.0       84.25  163.35
99.0       84.71  155.53
100.0      85.05  146.45
101.0      84.53  152.65
102.0      83.71  160.59
103.0      82.79  166.60
104.0      81.81  171.23
105.0      81.32  175.20
106.0      81.60  179.66
107.0      81.82  184.38
108.0      81.98  189.32
109.0      82.08  194.43
110.0      82.12  199.63
111.0      82.03  203.00
112.0      81.66  199.22
113.0      81.26  195.76
114.0      80.83  192.62
115.0      80.37  189.76
116.0      79.90  187.17
117.0      79.19  187.67
118.0      78.34  189.84
119.0      77.47  191.71
120.0      76.59  193.35
121.0      76.23  193.12
122.0      75.94  192.71
123.0      75.74  192.46
124.0      75.95  192.77
125.0      76.16  193.09
126.0      76.38  193.42
127.0      76.59  193.76
128.0      76.79  194.12
129.0      77.00  194.48
130.0      77.21  194.85
131.0      77.38  195.04
132.0      77.22  193.47
133.0      77.04  191.93
134.0      76.86  190.44
135.0      76.26  192.29
136.0      75.46  195.27
137.0      74.62  197.94
138.0      73.76  200.34
139.0      72.87  202.49
140.0      71.59  202.74
141.0      70.15  202.29
142.0      68.70  201.90
143.0      69.87  198.07
144.0      70.94  193.81
145.0      71.91  189.09
146.0      72.75  183.89
147.0      73.44  178.23
148.0      73.97  172.14
149.0      74.31  165.73
150.0      74.47  159.11
151.0      74.42  152.44
152.0      74.17  145.90
153.0      73.74  139.63
154.0      73.26  134.46
155.0      73.88  136.15
156.0      74.11  138.70
157.0      73.41  142.81
158.0      72.65  146.58
159.0      71.89  149.70
160.0      71.74  149.67
161.0      71.60  149.65
162.0      71.46  149.63
163.0      71.31  149.61
164.0      71.17  149.58
165.0      71.03  149.56
166.0      70.89  149.54
167.0      70.74  149.52
168.0      70.60  149.50
169.0      70.64  140.48
170.0      70.23  131.62
171.0      69.98  125.23
172.0      69.67  119.51
173.0      69.17  114.01
174.0      68.51  108.79
175.0      67.69  103.90
176.0      66.74   99.36
177.0      66.01   95.57
178.0      66.01   92.81
179.0      65.66   91.06
180.0      65.09   90.02
181.0      64.52   89.02
182.0      63.93   88.07
183.0      63.89   88.62
184.0      64.20   90.17
185.0      64.49   91.77
186.0      64.77   93.39
187.0      65.02   95.05
188.0      65.26   96.73
189.0      65.48   98.45
190.0      65.67  100.19
191.0      65.85  101.96
192.0      65.88  103.25
193.0      65.85  104.31
194.0      65.82  105.38
195.0      64.95  105.43
196.0      63.53  104.86
197.0      62.11  104.35
198.0      60.68  103.89
"""
    if plate=='GL':
       apwp="""
0.0        90.00    0.00
1.0        88.33  180.70
2.0        86.67  180.70
3.0        86.14  175.33
4.0        85.95  173.39
5.0        85.79  171.94
6.0        85.62  170.59
7.0        85.45  169.35
8.0        85.28  168.19
9.0        85.11  167.12
10.0       84.94  166.12
11.0       84.76  165.19
12.0       84.57  164.34
13.0       84.22  163.81
14.0       83.88  163.34
15.0       83.49  162.61
16.0       82.96  160.83
17.0       82.42  159.31
18.0       81.88  157.98
19.0       81.33  156.83
20.0       81.12  156.68
21.0       81.41  157.94
22.0       81.70  159.28
23.0       81.98  160.72
24.0       82.26  162.26
25.0       82.53  163.92
26.0       82.80  165.70
27.0       82.16  172.55
28.0       81.43  178.31
29.0       80.63  183.13
30.0       79.78  187.17
31.0       79.55  186.15
32.0       79.47  183.99
33.0       79.37  181.86
34.0       79.20  179.58
35.0       78.84  176.94
36.0       78.45  174.48
37.0       78.05  172.17
38.0       77.63  170.01
39.0       77.20  168.00
40.0       77.40  168.23
41.0       77.61  168.47
42.0       77.81  168.71
43.0       78.01  168.97
44.0       78.21  169.23
45.0       78.42  169.50
46.0       78.62  169.78
47.0       78.58  170.26
48.0       78.38  170.84
49.0       78.18  171.41
50.0       77.97  172.10
51.0       77.62  174.07
52.0       77.26  175.92
53.0       76.88  177.68
54.0       76.50  179.33
55.0       76.10  180.90
56.0       75.72  182.56
57.0       75.33  184.14
58.0       74.93  185.63
59.0       74.52  187.05
60.0       74.10  188.40
61.0       73.71  190.34
62.0       73.39  193.73
63.0       73.02  196.99
64.0       72.60  200.10
65.0       72.58  200.61
66.0       72.56  201.13
67.0       72.53  201.64
68.0       72.51  202.15
69.0       72.64  201.35
70.0       72.83  199.97
71.0       73.02  198.55
72.0       73.19  197.11
73.0       73.35  195.64
74.0       73.50  194.14
75.0       73.65  192.62
76.0       73.70  196.06
77.0       73.52  202.77
78.0       73.14  209.26
79.0       72.57  215.41
80.0       72.42  216.02
81.0       72.32  216.04
82.0       72.23  216.07
83.0       72.14  216.09
84.0       72.16  214.56
85.0       72.23  211.98
86.0       72.27  209.39
87.0       72.28  206.78
88.0       72.25  204.19
89.0       72.19  201.60
90.0       72.09  199.04
91.0       71.96  196.50
92.0       72.14  195.56
93.0       72.55  195.67
94.0       72.96  195.79
95.0       73.76  195.21
96.0       74.60  194.49
97.0       75.44  193.69
98.0       76.28  192.80
99.0       77.11  191.79
100.0      77.94  190.65
101.0      77.17  190.62
102.0      76.01  190.85
103.0      74.85  191.04
104.0      73.70  191.21
105.0      73.00  192.27
106.0      72.98  194.70
107.0      72.94  197.12
108.0      72.86  199.52
109.0      72.76  201.90
110.0      72.62  204.25
111.0      72.45  205.69
112.0      72.21  203.68
113.0      71.94  201.72
114.0      71.66  199.82
115.0      71.35  197.98
116.0      71.03  196.20
117.0      70.33  195.81
118.0      69.39  196.30
119.0      68.44  196.75
120.0      67.49  197.16
121.0      67.17  196.83
122.0      66.91  196.42
123.0      66.74  196.16
124.0      66.92  196.46
125.0      67.11  196.77
126.0      67.30  197.09
127.0      67.48  197.41
128.0      67.67  197.73
129.0      67.85  198.06
130.0      68.04  198.39
131.0      68.19  198.60
132.0      68.11  197.59
133.0      68.02  196.59
134.0      67.93  195.60
135.0      67.26  196.33
136.0      66.33  197.70
137.0      65.39  198.98
138.0      64.45  200.17
139.0      63.49  201.28
140.0      62.22  201.09
141.0      60.81  200.42
142.0      59.40  199.80
143.0      60.73  197.43
144.0      62.01  194.85
145.0      63.24  192.06
146.0      64.41  189.02
147.0      65.52  185.72
148.0      66.54  182.13
149.0      67.48  178.26
150.0      68.32  174.08
151.0      69.04  169.61
152.0      69.64  164.86
153.0      70.11  159.86
154.0      70.43  155.41
155.0      70.72  157.56
156.0      70.56  159.72
157.0      69.42  161.65
158.0      68.26  163.38
159.0      67.19  164.78
160.0      67.04  164.60
161.0      66.90  164.42
162.0      66.76  164.24
163.0      66.62  164.06
164.0      66.47  163.88
165.0      66.33  163.71
166.0      66.19  163.54
167.0      66.04  163.37
168.0      65.90  163.20
169.0      67.23  156.43
170.0      68.24  148.97
171.0      69.04  143.36
172.0      69.69  138.01
173.0      70.17  132.36
174.0      70.47  126.50
175.0      70.57  120.51
176.0      70.48  114.53
177.0      70.45  109.51
178.0      70.93  106.46
179.0      70.89  104.04
180.0      70.54  102.15
181.0      70.16  100.33
182.0      69.76   98.58
183.0      69.64   99.18
184.0      69.68  101.32
185.0      69.70  103.47
186.0      69.69  105.62
187.0      69.65  107.76
188.0      69.59  109.89
189.0      69.50  112.01
190.0      69.39  114.11
191.0      69.25  116.18
192.0      69.07  117.58
193.0      68.88  118.69
194.0      68.68  119.77
195.0      67.88  118.87
196.0      66.66  116.82
197.0      65.42  114.97
198.0      64.15  113.29
"""
    if plate=='IN':
       apwp="""
0.0        90.00    0.00
1.0        88.57  197.10
2.0        87.14  197.10
3.0        86.82  197.10
4.0        86.76  201.35
5.0        86.70  205.94
6.0        86.62  210.32
7.0        86.52  214.48
8.0        86.40  218.38
9.0        86.26  222.02
10.0       86.11  225.39
11.0       85.95  228.51
12.0       85.77  231.10
13.0       85.46  231.14
14.0       85.15  231.18
15.0       84.84  230.71
16.0       84.54  228.40
17.0       84.23  226.34
18.0       83.92  224.49
19.0       83.59  222.82
20.0       83.40  225.11
21.0       83.32  233.06
22.0       83.11  240.67
23.0       82.79  247.72
24.0       82.37  254.09
25.0       81.87  259.74
26.0       81.30  264.70
27.0       79.78  264.31
28.0       78.25  264.03
29.0       76.73  263.81
30.0       75.20  263.63
31.0       74.95  264.21
32.0       75.01  264.98
33.0       75.06  265.75
34.0       75.09  266.19
35.0       75.05  265.83
36.0       75.02  265.47
37.0       74.98  265.11
38.0       74.94  264.75
39.0       74.90  264.40
40.0       74.38  266.62
41.0       73.83  268.69
42.0       73.26  270.63
43.0       72.68  272.45
44.0       72.09  274.14
45.0       71.48  275.74
46.0       70.85  277.23
47.0       70.10  277.93
48.0       69.27  278.14
49.0       68.45  278.34
50.0       67.56  278.48
51.0       66.19  278.29
52.0       64.82  278.12
53.0       63.45  277.97
54.0       62.07  277.83
55.0       60.70  277.70
56.0       58.96  277.66
57.0       57.23  277.62
58.0       55.49  277.58
59.0       53.75  277.55
60.0       52.02  277.52
61.0       50.04  277.70
62.0       47.49  278.32
63.0       44.95  278.88
64.0       42.40  279.40
65.0       41.10  279.80
66.0       39.80  280.18
67.0       38.50  280.54
68.0       37.19  280.90
69.0       36.48  281.11
70.0       36.03  281.27
71.0       35.58  281.43
72.0       35.13  281.58
73.0       34.68  281.74
74.0       34.23  281.89
75.0       33.78  282.04
76.0       32.33  283.04
77.0       30.21  284.54
78.0       28.07  285.98
79.0       25.92  287.36
80.0       25.05  287.84
81.0       24.33  288.22
82.0       23.61  288.59
83.0       22.89  288.95
84.0       22.55  289.11
85.0       22.46  289.12
86.0       22.37  289.13
87.0       22.29  289.15
88.0       22.20  289.16
89.0       22.11  289.17
90.0       22.02  289.18
91.0       21.94  289.20
92.0       21.59  289.76
93.0       21.07  290.69
94.0       20.55  291.61
95.0       20.43  292.63
96.0       20.34  293.67
97.0       20.24  294.70
98.0       20.14  295.73
99.0       20.04  296.76
100.0      19.92  297.79
101.0      18.99  297.44
102.0      17.86  296.75
103.0      16.72  296.07
104.0      15.58  295.40
105.0      14.47  295.17
106.0      13.41  295.58
107.0      12.35  295.98
108.0      11.28  296.39
109.0      10.22  296.79
110.0       9.15  297.18
111.0       8.25  297.49
112.0       7.98  297.44
113.0       7.71  297.38
114.0       7.44  297.33
115.0       7.18  297.27
116.0       6.91  297.22
117.0       6.09  297.02
118.0       4.90  296.72
119.0       3.71  296.43
120.0       2.52  296.13
121.0       1.90  296.20
122.0       1.34  296.31
123.0       0.80  296.53
124.0       0.32  297.16
125.0      -0.16  297.78
126.0      -0.64  298.41
127.0      -1.12  299.04
128.0      -1.60  299.67
129.0      -2.09  300.30
130.0      -2.57  300.93
131.0      -3.01  301.50
132.0      -3.16  301.53
133.0      -3.31  301.56
134.0      -3.46  301.59
135.0      -4.41  301.48
136.0      -5.71  301.30
137.0      -7.01  301.12
138.0      -8.31  300.94
139.0      -9.61  300.75
140.0     -10.62  299.98
141.0     -11.51  298.94
142.0     -12.40  297.90
143.0     -10.89  298.80
144.0      -9.37  299.69
145.0      -7.85  300.58
146.0      -6.33  301.45
147.0      -4.81  302.32
148.0      -3.29  303.19
149.0      -1.76  304.06
150.0      -0.24  304.92
151.0       1.28  305.78
152.0       2.81  306.65
153.0       4.33  307.52
154.0       5.61  308.38
155.0       4.72  309.22
156.0       3.82  309.62
157.0       2.88  309.03
158.0       1.94  308.43
159.0       1.08  307.93
160.0       0.88  308.24
161.0       0.68  308.55
162.0       0.49  308.85
163.0       0.29  309.16
164.0       0.09  309.47
165.0      -0.11  309.78
166.0      -0.30  310.08
167.0      -0.50  310.39
168.0      -0.70  310.70
169.0       1.16  311.47
170.0       3.03  312.25
171.0       4.29  313.12
172.0       5.40  314.02
173.0       6.51  314.92
174.0       7.62  315.83
175.0       8.72  316.74
176.0       9.83  317.65
177.0      10.65  318.58
178.0      10.83  319.52
179.0      11.31  320.00
180.0      11.98  320.18
181.0      12.66  320.35
182.0      13.33  320.53
183.0      13.28  320.28
184.0      12.74  319.76
185.0      12.21  319.24
186.0      11.67  318.72
187.0      11.13  318.20
188.0      10.59  317.69
189.0      10.05  317.17
190.0       9.51  316.66
191.0       8.96  316.15
192.0       8.62  315.75
193.0       8.36  315.40
194.0       8.10  315.04
195.0       8.76  314.48
196.0      10.03  313.78
197.0      11.30  313.07
198.0      12.56  312.35
"""
    if plate=='NA':
       apwp="""
0.0        90.00    0.00
1.0        88.33  180.70
2.0        86.67  180.70
3.0        86.14  175.33
4.0        85.95  173.39
5.0        85.79  171.94
6.0        85.62  170.59
7.0        85.45  169.35
8.0        85.28  168.19
9.0        85.11  167.12
10.0       84.94  166.12
11.0       84.76  165.19
12.0       84.57  164.34
13.0       84.22  163.81
14.0       83.88  163.34
15.0       83.49  162.61
16.0       82.96  160.83
17.0       82.42  159.31
18.0       81.88  157.98
19.0       81.33  156.83
20.0       81.12  156.68
21.0       81.41  157.94
22.0       81.70  159.28
23.0       81.98  160.72
24.0       82.26  162.26
25.0       82.53  163.92
26.0       82.80  165.70
27.0       82.16  172.55
28.0       81.43  178.31
29.0       80.63  183.13
30.0       79.78  187.17
31.0       79.55  186.15
32.0       79.47  183.99
33.0       79.37  181.86
34.0       79.20  179.56
35.0       78.86  176.88
36.0       78.50  174.36
37.0       78.12  171.99
38.0       77.72  169.78
39.0       77.30  167.70
40.0       77.61  167.72
41.0       77.92  167.75
42.0       78.23  167.77
43.0       78.54  167.80
44.0       78.85  167.83
45.0       79.16  167.86
46.0       79.48  167.89
47.0       79.55  168.32
48.0       79.47  169.01
49.0       79.38  169.70
50.0       79.28  170.59
51.0       79.05  173.39
52.0       78.79  176.08
53.0       78.52  178.64
54.0       78.22  181.08
55.0       77.90  183.40
56.0       77.51  185.86
57.0       77.09  188.16
58.0       76.65  190.32
59.0       76.20  192.35
60.0       75.74  194.24
61.0       75.25  196.69
62.0       74.73  200.49
63.0       74.14  204.02
64.0       73.50  207.30
65.0       73.48  207.86
66.0       73.46  208.42
67.0       73.43  208.98
68.0       73.41  209.53
69.0       73.65  208.66
70.0       74.01  207.12
71.0       74.35  205.51
72.0       74.68  203.84
73.0       75.00  202.09
74.0       75.30  200.27
75.0       75.59  198.38
76.0       75.52  201.87
77.0       75.06  208.70
78.0       74.41  215.06
79.0       73.59  220.85
80.0       73.50  221.21
81.0       73.50  221.00
82.0       73.50  220.79
83.0       73.50  220.58
84.0       73.72  218.91
85.0       74.06  216.16
86.0       74.37  213.31
87.0       74.63  210.35
88.0       74.86  207.30
89.0       75.04  204.16
90.0       75.18  200.96
91.0       75.27  197.71
92.0       75.55  196.67
93.0       75.95  197.15
94.0       76.36  197.65
95.0       77.18  197.76
96.0       78.05  197.83
97.0       78.92  197.91
98.0       79.79  198.01
99.0       80.66  198.13
100.0      81.53  198.27
101.0      80.82  196.53
102.0      79.71  194.75
103.0      78.60  193.30
104.0      77.48  192.12
105.0      76.75  192.71
106.0      76.59  195.69
107.0      76.40  198.60
108.0      76.18  201.42
109.0      75.93  204.14
110.0      75.65  206.77
111.0      75.39  208.27
112.0      75.32  205.66
113.0      75.23  203.07
114.0      75.11  200.52
115.0      74.96  198.02
116.0      74.78  195.56
117.0      74.13  194.52
118.0      73.19  194.41
119.0      72.24  194.30
120.0      71.29  194.21
121.0      70.97  193.62
122.0      70.71  192.99
123.0      70.54  192.59
124.0      70.71  193.06
125.0      70.89  193.53
126.0      71.06  194.01
127.0      71.24  194.50
128.0      71.41  195.00
129.0      71.58  195.51
130.0      71.75  196.03
131.0      71.90  196.38
132.0      71.88  195.14
133.0      71.85  193.90
134.0      71.81  192.67
135.0      71.10  193.14
136.0      70.08  194.23
137.0      69.06  195.23
138.0      68.04  196.14
139.0      67.01  196.96
140.0      65.77  196.26
141.0      64.44  195.02
142.0      63.10  193.90
143.0      64.58  191.66
144.0      66.02  189.16
145.0      67.42  186.37
146.0      68.76  183.24
147.0      70.04  179.71
148.0      71.23  175.75
149.0      72.34  171.28
150.0      73.33  166.27
151.0      74.19  160.69
152.0      74.88  154.55
153.0      75.40  147.91
154.0      75.73  141.88
155.0      76.02  144.73
156.0      75.85  147.65
157.0      74.69  150.19
158.0      73.49  152.38
159.0      72.39  154.07
160.0      72.26  153.82
161.0      72.13  153.57
162.0      71.99  153.32
163.0      71.86  153.07
164.0      71.73  152.83
165.0      71.60  152.59
166.0      71.47  152.36
167.0      71.33  152.13
168.0      71.20  151.90
169.0      72.50  143.28
170.0      73.38  133.55
171.0      74.04  126.09
172.0      74.51  118.88
173.0      74.74  111.36
174.0      74.71  103.74
175.0      74.42   96.27
176.0      73.90   89.17
177.0      73.49   83.36
178.0      73.72   79.48
179.0      73.50   76.79
180.0      72.99   75.03
181.0      72.46   73.37
182.0      71.92   71.80
183.0      71.85   72.55
184.0      72.07   74.85
185.0      72.26   77.20
186.0      72.43   79.60
187.0      72.56   82.04
188.0      72.67   84.51
189.0      72.74   87.01
190.0      72.79   89.52
191.0      72.80   92.04
192.0      72.74   93.81
193.0      72.65   95.23
194.0      72.54   96.64
195.0      71.70   96.06
196.0      70.36   94.36
197.0      69.01   92.87
198.0      67.64   91.56
"""
    if plate=='SA':
       apwp="""
0.0        90.00    0.00
1.0        88.48  176.30
2.0        86.95  176.30
3.0        86.53  168.76
4.0        86.45  164.50
5.0        86.37  160.76
6.0        86.28  157.18
7.0        86.17  153.79
8.0        86.06  150.58
9.0        85.93  147.57
10.0       85.79  144.75
11.0       85.64  142.12
12.0       85.48  139.77
13.0       85.24  138.58
14.0       84.99  137.49
15.0       84.69  136.40
16.0       84.13  135.05
17.0       83.57  133.95
18.0       83.00  133.01
19.0       82.44  132.22
20.0       82.25  131.54
21.0       82.61  130.86
22.0       82.97  130.10
23.0       83.33  129.26
24.0       83.69  128.32
25.0       84.05  127.28
26.0       84.40  126.10
27.0       84.43  135.88
28.0       84.29  145.47
29.0       84.01  154.39
30.0       83.60  162.34
31.0       83.39  160.95
32.0       83.23  157.53
33.0       83.04  154.27
34.0       82.75  151.13
35.0       82.23  148.16
36.0       81.69  145.56
37.0       81.14  143.29
38.0       80.57  141.28
39.0       80.00  139.50
40.0       80.29  138.06
41.0       80.58  136.53
42.0       80.86  134.91
43.0       81.14  133.19
44.0       81.40  131.36
45.0       81.66  129.42
46.0       81.90  127.36
47.0       82.03  126.70
48.0       82.09  127.04
49.0       82.15  127.39
50.0       82.22  128.02
51.0       82.37  131.28
52.0       82.49  134.65
53.0       82.59  138.13
54.0       82.66  141.69
55.0       82.70  145.30
56.0       82.74  149.45
57.0       82.73  153.61
58.0       82.69  157.75
59.0       82.61  161.83
60.0       82.50  165.80
61.0       82.43  170.84
62.0       82.42  178.70
63.0       82.28  186.40
64.0       82.00  193.70
65.0       82.08  194.90
66.0       82.15  196.11
67.0       82.22  197.36
68.0       82.28  198.62
69.0       82.50  196.70
70.0       82.76  193.22
71.0       82.99  189.49
72.0       83.19  185.52
73.0       83.36  181.34
74.0       83.48  176.96
75.0       83.58  172.44
76.0       83.88  180.55
77.0       83.90  198.12
78.0       83.37  214.31
79.0       82.41  227.29
80.0       82.34  228.63
81.0       82.39  228.88
82.0       82.44  229.14
83.0       82.48  229.40
84.0       82.82  226.98
85.0       83.33  222.26
86.0       83.78  216.82
87.0       84.17  210.58
88.0       84.48  203.56
89.0       84.70  195.83
90.0       84.82  187.59
91.0       84.83  179.15
92.0       85.11  176.27
93.0       85.63  177.19
94.0       86.15  178.37
95.0       87.04  175.29
96.0       87.94  168.69
97.0       88.78  152.46
98.0       89.26  101.14
99.0       88.81   47.96
100.0      87.98   31.01
101.0      88.51   36.07
102.0      89.29   63.58
103.0      89.30  145.49
104.0      88.53  174.06
105.0      88.07  189.19
106.0      88.01  213.41
107.0      87.64  233.01
108.0      87.08  246.23
109.0      86.42  254.90
110.0      85.70  260.77
111.0      85.15  264.12
112.0      85.38  263.70
113.0      85.61  263.23
114.0      85.84  262.72
115.0      86.08  262.14
116.0      86.31  261.48
117.0      86.05  255.65
118.0      85.41  248.40
119.0      84.71  242.98
120.0      83.97  238.86
121.0      83.74  236.57
122.0      83.55  234.54
123.0      83.39  233.53
124.0      83.33  236.16
125.0      83.26  238.74
126.0      83.18  241.27
127.0      83.09  243.73
128.0      82.98  246.12
129.0      82.86  248.43
130.0      82.73  250.66
131.0      82.62  252.43
132.0      82.80  250.74
133.0      82.98  248.95
134.0      83.15  247.08
135.0      82.42  244.60
136.0      81.28  242.47
137.0      80.14  240.84
138.0      79.00  239.54
139.0      77.85  238.48
140.0      76.82  234.91
141.0      75.79  230.78
142.0      74.70  227.20
143.0      76.33  226.82
144.0      77.95  226.34
145.0      79.58  225.72
146.0      81.20  224.87
147.0      82.82  223.63
148.0      84.44  221.68
149.0      86.04  218.15
150.0      87.61  209.92
151.0      88.97  176.54
152.0      88.68   89.32
153.0      87.22   67.59
154.0      85.89   60.82
155.0      86.78   50.54
156.0      87.70   41.70
157.0      88.96   60.27
158.0      89.26  158.76
159.0      88.19  190.34
160.0      88.08  197.32
161.0      87.94  203.47
162.0      87.79  208.80
163.0      87.62  213.39
164.0      87.43  217.35
165.0      87.23  220.75
166.0      87.03  223.70
167.0      86.82  226.26
168.0      86.60  228.50
169.0      88.64  230.93
170.0      89.31   38.96
171.0      87.78   36.39
172.0      86.36   34.32
173.0      84.94   33.40
174.0      83.53   32.89
175.0      82.11   32.55
176.0      80.69   32.32
177.0      79.48   31.11
178.0      78.71   27.80
179.0      78.03   27.66
180.0      77.42   29.28
181.0      76.79   30.75
182.0      76.16   32.10
183.0      76.35   32.76
184.0      77.09   33.06
185.0      77.83   33.40
186.0      78.58   33.77
187.0      79.32   34.20
188.0      80.06   34.69
189.0      80.80   35.27
190.0      81.54   35.93
191.0      82.28   36.73
192.0      82.77   37.91
193.0      83.16   39.32
194.0      83.55   40.91
195.0      83.19   47.69
196.0      82.21   55.93
197.0      81.11   62.23
198.0      79.92   67.11
"""
    return apwp
#
def bc02(data):
    """
     get APWP from Besse and Courtillot 2002 paper
    """

    plate,site_lat,site_lon,age=data[0],data[1],data[2],data[3]
    apwp=get_plate_data(plate)
    recs=apwp.split()
    #
    # put it into  usable form in plate_data
    #
    k,plate_data=0,[]
    while k<len(recs)-3:
        rec=[float(recs[k]),float(recs[k+1]),float(recs[k+2])]
        plate_data.append(rec)
        k=k+3

    #
    # find the right pole for the age
    #
    for i in range(len(plate_data)):
        if age >= plate_data[i][0] and age <= plate_data[i+1][0]:
           if (age-plate_data[i][0]) < (plate_data[i][0]-age):
              rec=i
           else:
              rec=i+1
           break
    pole_lat=plate_data[rec][1]
    pole_lon=plate_data[rec][2]
    return pole_lat,pole_lon

def linreg(x,y):
    """
    does a linear regression
    """
    if len(x)!=len(y):
        print 'x and y must be same length'
        sys.exit()
    xx,yy,xsum,ysum,xy,n,sum=0,0,0,0,0,len(x),0
    linpars={}
    for i in range(n):
        xx+=x[i]*x[i]
        yy+=y[i]*y[i]
        xy+=x[i]*y[i]
        xsum+=x[i]
        ysum+=y[i]
        xsig=numpy.sqrt((xx-xsum**2/n)/(n-1.))
        ysig=numpy.sqrt((yy-ysum**2/n)/(n-1.))
    linpars['slope']=(xy-(xsum*ysum/n))/(xx-(xsum**2)/n)
    linpars['b']=(ysum-linpars['slope']*xsum)/n
    linpars['r']=(linpars['slope']*xsig)/ysig
    for i in range(n):
        a=y[i]-linpars['b']-linpars['slope']*x[i]
        sum+=a
    linpars['sigma']=sum/(n-2.)
    linpars['n']=n
    return linpars


def squish(incs,f):
    """
    returns 'flattened' inclination, assuming factor, f and King (1955) formula
    """
    incs=incs*numpy.pi/180. # convert to radians
    tincnew=f*numpy.tan(incs) # multiply tangent by flattening factor
    return numpy.arctan(tincnew)*180./numpy.pi


def get_TS(ts):
    if ts=='ck95':
        TS=[0,0.780,0.990,1.070,1.770,1.950,2.140,2.150,2.581,3.040,3.110,3.220,3.330,3.580,4.180,4.290,4.480,4.620,4.800,4.890,4.980,5.230,5.894,6.137,6.269,6.567,6.935,7.091,7.135,7.170,7.341,7.375,7.432,7.562,7.650,8.072,8.225,8.257,8.699,9.025,9.230,9.308,9.580,9.642,9.740,9.880,9.920,10.949,11.052,11.099,11.476,11.531,11.935,12.078,12.184,12.401,12.678,12.708,12.775,12.819,12.991,13.139,13.302,13.510,13.703,14.076,14.178,14.612,14.800,14.888,15.034,15.155,16.014,16.293,16.327,16.488,16.556,16.726,17.277,17.615,18.281,18.781,19.048,20.131,20.518,20.725,20.996,21.320,21.768,21.859,22.151,22.248,22.459,22.493,22.588,22.750,22.804,23.069,23.353,23.535,23.677,23.800,23.999,24.118,24.730,24.781,24.835,25.183,25.496,25.648,25.823,25.951,25.992,26.554,27.027,27.972,28.283,28.512,28.578,28.745,29.401,29.662,29.765,30.098,30.479,30.939,33.058,33.545,34.655,34.940,35.343,35.526,35.685,36.341,36.618,37.473,37.604,37.848,37.920,38.113,38.426,39.552,39.631,40.130,41.257,41.521,42.536,43.789,46.264,47.906,49.037,49.714,50.778,50.946,51.047,51.743,52.364,52.663,52.757,52.801,52.903,53.347,55.904,56.391,57.554,57.911,60.920,61.276,62.499,63.634,63.976,64.745,65.578,67.610,67.735,68.737,71.071,71.338,71.587,73.004,73.291,73.374,73.619,79.075,83.000]
        Labels=[['C1n',0],['C1r',0.78],['C2',1.77],['C2An',2.581],['C2Ar',3.58],['C3n',4.18],['C3r',5.23],['C3An',5.894],['C3Ar',6.567],['C3Bn',6.935],['C3Br',7.091],['C4n',7.432],['C4r',8.072],['C4An',8.699],['C4Ar',9.025],['C5n',9.74],['C5r',10.949],['C5An',11.935],['C5Ar',12.401],['C5AAn',12.991],['C5AAr',13.139],['C5ABn',13.302],['C5ABr',13.51],['C5ACn',13.703],['C5ACr',14.076],['C5ADn',14.178],['C5ADr',14.612],['C5Bn',14.8],['C5Br',15.155],['C5Cn',16.014],['C5Cr',16.726],['C5Dn',17.277],['C5Dr',17.615],['C5En',18.281],['C5Er',18.781],['C6n',19.048],['C6r',20.131],['C6An',20.518],['C6Ar',21.32],['C6AAn',21.768],['C6AAr',21.859],['C6Bn',22.588],['C6Br',23.069],['C6Cn',23.353],['C6Cr',24.118],['C7n',24.73],['C7r',25.183],['C7A',25.496],['C8n',25.823],['C8r',26.554],['C9n',27.027],['C9r',27.972],['C10n',28.283],['C10r',28.745],['C11n',29.401],['C11r',30.098],['C12n',30.479],['C12r',30.939],['C13n',33.058],['C13r',33.545],['C15n',34.655],['C15r',34.94],['C16n',35.343],['C16r',36.341],['C17n',36.618],['C17r',38.113],['C18n',38.426],['C18r',40.13],['C19n',41.257],['C19r',41.521],['C20n',42.536],['C20r',43.789],['C21n',46.264],['C21r',47.906],['C22n',49.037],['C22r',49.714],['C23n',50.778],['C23r',51.743],['C24n',52.364],['C24r',53.347],['C25n',55.904],['C25r',56.391],['C26n',57.554],['C26r',57.911],['C27n',60.92],['C27r',61.276],['C28n',62.499],['C28r',63.634],['C29n',63.976],['C29r',64.745],['C30n',65.578],['C30r',67.61],['C31n',67.735],['C31r',68.737],['C32n',71.071],['C32r',73.004],['C33n',73.619],['C33r',79.075],['C34n',83]]
        return TS,Labels
    if ts=='gts04':
        TS=[0,0.781,0.988,1.072,1.778,1.945,2.128,2.148,2.581,3.032,3.116,3.207,3.33,3.596,4.187,4.3,4.493,4.631,4.799,4.896,4.997,5.235,6.033,6.252,6.436,6.733,7.14,7.212,7.251,7.285,7.454,7.489,7.528,7.642,7.695,8.108,8.254,8.3,8.769,9.098,9.312,9.409,9.656,9.717,9.779,9.934,9.987,11.04,11.118,11.154,11.554,11.614,12.014,12.116,12.207,12.415,12.73,12.765,12.82,12.878,13.015,13.183,13.369,13.605,13.734,14.095,14.194,14.581,14.784,14.877,15.032,15.16,15.974,16.268,16.303,16.472,16.543,16.721,17.235,17.533,17.717,17.74,18.056,18.524,18.748,20,20.04,20.213,20.439,20.709,21.083,21.159,21.403,21.483,21.659,21.688,21.767,21.936,21.992,22.268,22.564,22.754,22.902,23.03,23.249,23.375,24.044,24.102,24.163,24.556,24.915,25.091,25.295,25.444,25.492,26.154,26.714,27.826,28.186,28.45,28.525,28.715,29.451,29.74,29.853,30.217,30.627,31.116,33.266,33.738,34.782,35.043,35.404,35.567,35.707,36.276,36.512,37.235,37.345,37.549,37.61,37.771,38.032,38.975,39.041,39.464,40.439,40.671,41.59,42.774,45.346,47.235,48.599,49.427,50.73,50.932,51.057,51.901,52.648,53.004,53.116,53.167,53.286,53.808,56.665,57.18,58.379,58.737,61.65,61.983,63.104,64.128,64.432,65.118,65.861,67.696,67.809,68.732,70.961,71.225,71.474,72.929,73.231,73.318,73.577,79.543,84]
        Labels=[['C1n',0.000],['C1r',0.781],['C2',1.778],['C2An',2.581],['C2Ar',3.596],['C3n',4.187],['C3r',5.235],['C3An',6.033],['C3Ar',6.733],['C3Bn',7.140],['C3Br',7.212],['C4n',7.528],['C4r',8.108],['C4An',8.769],['C4Ar',9.098],['C5n',9.779],['C5r',11.040],['C5An',12.014],['C5Ar',12.415],['C5AAn',13.015],['C5AAr',13.183],['C5ABn',13.369],['C5ABr',13.605],['C5ACn',13.734],['C5ACr',14.095],['C5ADn',14.194],['C5ADr',14.581],['C5Bn',14.784],['C5Br',15.160],['C5Cn',15.974],['C5Cr',16.721],['C5Dn',17.235],['C5Dr',17.533],['C5En',18.056],['C5Er',18.524],['C6n',18.748],['C6r',19.772],['C6An',20.040],['C6Ar',20.709],['C6AAn',21.083],['C6AAr',21.159],['C6Bn',21.767],['C6Br',22.268],['C6Cn',22.564],['C6Cr',23.375],['C7n',24.044],['C7r',24.556],['C7A',24.919],['C8n',25.295],['C8r',26.154],['C9n',26.714],['C9r',27.826],['C10n',28.186],['C11n',29.451],['C11r',30.217],['C12n',30.627],['C12r',31.116],['C13n',33.266],['C13r',33.738],['C15n',34.782],['C15r',35.043],['C16n',35.404],['C16r',36.276],['C17n',36.512],['C17r',37.771],['C18n',38.032],['C18r',39.464],['C19n',40.439],['C19r',40.671],['C20n',41.590],['C20r',42.774],['C21n',45.346],['C21r',47.235],['C22n',48.599],['C22r',49.427],['C23n',50.730],['C23r',51.901],['C24n',52.648],['C24r',53.808],['C25n',56.665],['C25r',57.180],['C26n',58.379],['C26r',58.737],['C27n',61.650],['C27r',61.938],['C28n',63.104],['C28r',64.128],['C29n',64.432],['C29r',65.118],['C30n',65.861],['C30r',67.696],['C31n',67.809],['C31r',68.732],['C32n',70.961],['C32r',72.929],['C33n',73.577],['C33r',79.543],['C34n',84.000]]
        return TS,Labels
    if ts=='gts12':
        TS=[0, 0.781, 0.988, 1.072, 1.173, 1.185, 1.778, 1.945, 2.128, 2.148, 2.581, 3.032, 3.116, 3.207, 3.330, 3.596, 4.187, 4.300, 4.493, 4.631, 4.799, 4.896, 4.997, 5.235, 6.033, 6.252, 6.436, 6.733, 7.140, 7.212, 7.251, 7.285, 7.454, 7.489, 7.528, 7.642, 7.695, 8.108, 8.254, 8.300, 8.771, 9.105, 9.311, 9.426, 9.647, 9.721, 9.786, 9.937, 9.984, 11.056, 11.146, 11.188, 11.592, 11.657, 12.049, 12.174, 12.272, 12.474, 12.735, 12.770, 12.829, 12.887, 13.032, 13.183, 13.363, 13.608, 13.739, 14.070, 14.163, 14.609, 14.775, 14.870, 15.032, 15.160, 15.974, 16.268, 16.303, 16.472, 16.543, 16.721, 17.235, 17.533, 17.717, 17.740, 18.056, 18.524, 18.748, 19.722, 20.040, 20.213, 20.439, 20.709, 21.083, 21.159, 21.403, 21.483, 21.659, 21.688, 21.767, 21.936, 21.992, 22.268, 22.564, 22.754, 22.902, 23.030, 23.233, 23.295, 23.962, 24.000, 24.109, 24.474, 24.761, 24.984, 25.099, 25.264, 25.304, 25.987, 26.420, 27.439, 27.859, 28.087, 28.141, 28.278, 29.183, 29.477, 29.527, 29.970, 30.591, 31.034, 33.157, 33.705, 34.999, 35.294, 35.706, 35.892, 36.051, 36.700, 36.969, 37.753, 37.872, 38.093, 38.159, 38.333, 38.615, 39.627, 39.698, 40.145, 41.154, 41.390, 42.301, 43.432, 45.724, 47.349, 48.566, 49.344, 50.628, 50.835, 50.961, 51.833, 52.620, 53.074, 53.199, 53.274, 53.416, 53.983, 57.101, 57.656, 58.959, 59.237, 62.221, 62.517, 63.494, 64.667, 64.958, 65.688, 66.398, 68.196, 68.369, 69.269, 71.449, 71.689, 71.939, 73.649, 73.949, 74.049, 74.309, 79.900, 83.64]
        Labels=[['C1n',0.000],['C1r',0.781],['C2',1.778],['C2An',2.581],['C2Ar',3.596],['C3n',4.187],['C3r',5.235],['C3An',6.033],['C3Ar',6.733],['C3Bn',7.140],['C3Br',7.212],['C4n',7.528],['C4r',8.108],['C4An',8.771],['C4Ar',9.105],['C5n',9.786],['C5r',11.056],['C5An',12.049],['C5Ar',12.474],['C5AAn',13.032],['C5AAr',13.183],['C5ABn',13.363],['C5ABr',13.608],['C5ACn',13.739],['C5ACr',14.070],['C5ADn',14.163],['C5ADr',14.609],['C5Bn',14.775],['C5Br',15.160],['C5Cn',15.974],['C5Cr',16.721],['C5Dn',17.235],['C5Dr',17.533],['C5En',18.056],['C5Er',18.524],['C6n',18.748],['C6r',19.722],['C6An',20.040],['C6Ar',20.709],['C6AAn',21.083],['C6AAr',21.159],['C6Bn',21.767],['C6Br',22.268],['C6Cn',22.564],['C6Cr',23.295],['C7n',23.962],['C7r',24.474],['C7An',24.761],['C7Ar',24.984],['C8n',25.099],['C8r',25.987],['C9n',26.420],['C9r',27.439],['C10n',27.859],['C10r',28.278],['C11n',29.183],['C11r',29.970],['C12n',30.591],['C12r',31.034],['C13n',33.157],['C13r',33.705],['C15n',34.999],['C15r',35.294],['C16n',35.706],['C16r',36.700],['C17n',36.969],['C17r',38.333],['C18n',38.615],['C18r',40.145],['C19n',41.154],['C19r',41.390],['C20n',42.301],['C20r',43.432],['C21n',45.724],['C21r',47.349],['C22n',48.566],['C22r',49.344],['C23n',50.628],['C23r',51.833],['C24n',52.620],['C24r',53.983],['C25n',57.101],['C25r',57.656],['C26n',58.959],['C26r',59.237],['C27n',62.221],['C27r',62.517],['C28n',63.494],['C28r',64.667],['C29n',64.958],['C29r',65.688],['C30n',66.398],['C30r',68.196],['C31n',68.369],['C31r',69.269],['C32n',71.449],['C32r',73.649],['C33n',74.309],['C33r',79.900],['C34n',83.64]]
        return TS,Labels
    print "Time Scale Option Not Available"
    sys.exit()

def initialize_acceptance_criteria ():
    '''
    initialize acceptance criteria with NULL values for thellier_gui and demag_gui

    acceptancec criteria format is doctionaries:

    acceptance_criteria={}
        acceptance_criteria[crit]={}
            acceptance_criteria[crit]['category']=
            acceptance_criteria[crit]['criterion_name']=
            acceptance_criteria[crit]['value']=
            acceptance_criteria[crit]['threshold_type']
            acceptance_criteria[crit]['decimal_points']

   'category':
       'DE-SPEC','DE-SAMP'..etc
   'criterion_name':
       MagIC name
   'value':
        a number (for 'regular criteria')
        a string (for 'flag')
        1 for True (if criteria is bullean)
        0 for False (if criteria is bullean)
        -999 means N/A
   'threshold_type':
       'low'for low threshold value
       'high'for high threshold value
        [flag1.flag2]: for flags
        'bool' for bollean flags (can be 'g','b' or True/Flase or 1/0)
   'decimal_points':
       number of decimal points in rounding
       (this is used in displaying criteria in the dialog box)
       -999 means Exponent with 3 descimal points for floats and string for string
    '''

    acceptance_criteria={}
    # --------------------------------
    # 'DE-SPEC'
    # --------------------------------

    # low cutoff value
    category='DE-SPEC'
    for crit in ['specimen_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    category='DE-SPEC'
    for crit in ['specimen_mad','specimen_dang','specimen_alpha95']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        acceptance_criteria[crit]['decimal_points']=1

    # flag
    for crit in ['specimen_direction_type']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        if crit=='specimen_direction_type':
            acceptance_criteria[crit]['threshold_type']=['l','p']
        if crit=='specimen_polarity':
            acceptance_criteria[crit]['threshold_type']=['n','r','t','e','i']
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'DE-SAMP'
    # --------------------------------

    # low cutoff value
    category='DE-SAMP'
    for crit in ['sample_n','sample_n_lines','sample_n_planes']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    category='DE-SAMP'
    for crit in ['sample_r','sample_alpha95','sample_sigma','sample_k','sample_tilt_correction']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['sample_tilt_correction']:
            acceptance_criteria[crit]['decimal_points']=0
        elif crit in ['sample_alpha95']:
            acceptance_criteria[crit]['decimal_points']=1
        else:
            acceptance_criteria[crit]['decimal_points']=-999

    # flag
    for crit in ['sample_direction_type','sample_polarity']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        if crit=='sample_direction_type':
            acceptance_criteria[crit]['threshold_type']=['l','p']
        if crit=='sample_polarity':
            acceptance_criteria[crit]['threshold_type']=['n','r','t','e','i']
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'DE-SITE'
    # --------------------------------

    # low cutoff value
    category='DE-SITE'
    for crit in ['site_n','site_n_lines','site_n_planes']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['site_k','site_r','site_alpha95','site_sigma','site_tilt_correction']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['site_tilt_correction']:
            acceptance_criteria[crit]['decimal_points']=0
        else:
            acceptance_criteria[crit]['decimal_points']=1

    # flag
    for crit in ['site_direction_type','site_polarity']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        if crit=='site_direction_type':
            acceptance_criteria[crit]['threshold_type']=['l','p']
        if crit=='site_polarity':
            acceptance_criteria[crit]['threshold_type']=['n','r','t','e','i']
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'DE-STUDY'
    # --------------------------------
    category='DE-STUDY'
    # low cutoff value
    for crit in ['average_k','average_n','average_nn','average_nnn','average_r']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        if crit in ['average_n','average_nn','average_nnn']:
            acceptance_criteria[crit]['decimal_points']=0
        elif crit in ['average_alpha95']:
            acceptance_criteria[crit]['decimal_points']=1
        else:
            acceptance_criteria[crit]['decimal_points']=-999

    # high cutoff value
    for crit in ['average_alpha95','average_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['average_alpha95']:
            acceptance_criteria[crit]['decimal_points']=1
        else :
            acceptance_criteria[crit]['decimal_points']=-999


    # --------------------------------
    # 'IE-SPEC' (a long list from SPD.v.1.0)
    # --------------------------------
    category='IE-SPEC'

    # low cutoff value
    for crit in ['specimen_int_n','specimen_f','specimen_fvds','specimen_frac','specimen_q','specimen_w','specimen_r_sq','specimen_int_ptrm_n',\
    'specimen_int_ptrm_tail_n','specimen_ac_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0
        if crit in ['specimen_int_n','specimen_int_ptrm_n','specimen_int_ptrm_tail_n','specimen_ac_n']:
            acceptance_criteria[crit]['decimal_points']=0
        elif crit in ['specimen_f','specimen_fvds','specimen_frac','specimen_q']:
            acceptance_criteria[crit]['decimal_points']=2
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # high cutoff value
    for crit in ['specimen_b_sigma','specimen_b_beta','specimen_g','specimen_gmax','specimen_k','specimen_k_sse','specimen_k_prime','specimen_k_prime_sse',\
    'specimen_coeff_det_sq','specimen_z','specimen_z_md','specimen_int_mad','specimen_int_mad_anc','specimen_int_alpha','specimen_alpha','specimen_alpha_prime',\
    'specimen_theta','specimen_int_dang','specimen_int_crm','specimen_ptrm','specimen_dck','specimen_drat','specimen_maxdev','specimen_cdrat',\
    'specimen_drats','specimen_mdrat','specimen_mdev','specimen_dpal','specimen_tail_drat','specimen_dtr','specimen_md','specimen_dt','specimen_dac','specimen_gamma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['specimen_int_mad','specimen_int_mad_anc','specimen_int_dang','specimen_drat','specimen_cdrat','specimen_drats','specimen_tail_drat','specimen_dtr','specimen_md','specimen_dac','specimen_gamma']:
            acceptance_criteria[crit]['decimal_points']=1
        elif crit in ['specimen_gmax']:
            acceptance_criteria[crit]['decimal_points']=2
        elif crit in ['specimen_b_sigma','specimen_b_beta','specimen_g','specimen_k', 'specimen_k_prime']:
            acceptance_criteria[crit]['decimal_points']=3
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # flags
    for crit in ['specimen_scat']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']='bool'
        acceptance_criteria[crit]['decimal_points']=-999


    # --------------------------------
    # 'IE-SAMP'
    # --------------------------------
    category='IE-SAMP'

    # low cutoff value
    for crit in ['sample_int_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['sample_int_rel_sigma','sample_int_rel_sigma_perc','sample_int_sigma','sample_int_sigma_perc']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['sample_int_rel_sigma_perc','sample_int_sigma_perc']:
            acceptance_criteria[crit]['decimal_points']=1
        else :
            acceptance_criteria[crit]['decimal_points']=-999


    # --------------------------------
    # 'IE-SITE'
    # --------------------------------
    category='IE-SITE'

    # low cutoff value
    for crit in ['site_int_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['site_int_rel_sigma','site_int_rel_sigma_perc','site_int_sigma','site_int_sigma_perc']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['site_int_rel_sigma_perc','site_int_sigma_perc']:
            acceptance_criteria[crit]['decimal_points']=1
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'IE-STUDY'
    # --------------------------------
    category='IE-STUDY'
    # low cutoff value
    for crit in ['average_int_n','average_int_n','average_int_nn','average_int_nnn',]:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['average_int_rel_sigma','average_int_rel_sigma_perc','average_int_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        if crit in ['average_int_rel_sigma_perc']:
            acceptance_criteria[crit]['decimal_points']=1
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'NPOLE'
    # --------------------------------
    category='NPOLE'
    # flags
    for crit in ['site_polarity']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']=['n','r']
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'NPOLE'
    # --------------------------------
    category='RPOLE'
    # flags
    for crit in ['site_polarity']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']=['n','r']
        acceptance_criteria[crit]['decimal_points']=-999


    # --------------------------------
    # 'VADM'
    # --------------------------------
    category='VADM'
    # low cutoff value
    for crit in ['vadm_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        if crit in ['vadm_n']:
            acceptance_criteria[crit]['decimal_points']=0
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'VADM'
    # --------------------------------
    category='VADM'
    # low cutoff value
    for crit in ['vadm_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['vadm_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'VADM'
    # --------------------------------
    category='VDM'
    # low cutoff value
    for crit in ['vdm_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['vdm_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'VGP'
    # --------------------------------
    category='VDM'
    # low cutoff value
    for crit in ['vgp_n']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=0

    # high cutoff value
    for crit in ['vgp_alpha95','vgp_dm','vgp_dp','vgp_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        if crit in ['vgp_alpha95']:
            acceptance_criteria[crit]['decimal_points','vgp_dm','vgp_dp']=1
        else :
            acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'AGE'
    # --------------------------------
    category='AGE'
    # low cutoff value
    for crit in ['average_age_min']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="low"
        acceptance_criteria[crit]['decimal_points']=-999

    # high cutoff value
    for crit in ['average_age_max','average_age_sigma']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        acceptance_criteria[crit]['decimal_points']=-999

    # flags
    for crit in ['average_age_unit']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']=['Ga','Ka','Ma','Years AD (+/-)','Years BP','Years Cal AD (+/-)','Years Cal BP']
        acceptance_criteria[crit]['decimal_points']=-999

    # --------------------------------
    # 'ANI'
    # --------------------------------
    category='ANI'
    # high cutoff value
    for crit in ['anisotropy_alt','sample_aniso_mean','site_aniso_mean']: # value is in precent
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']="high"
        acceptance_criteria[crit]['decimal_points']=3

    # flags
    for crit in ['anisotropy_ftest_flag']:
        acceptance_criteria[crit]={}
        acceptance_criteria[crit]['category']=category
        acceptance_criteria[crit]['criterion_name']=crit
        acceptance_criteria[crit]['value']=-999
        acceptance_criteria[crit]['threshold_type']='bool'
        acceptance_criteria[crit]['decimal_points']=-999


    return(acceptance_criteria)



def read_criteria_from_file(path,acceptance_criteria):
    '''
    Read accceptance criteria from magic pmag_criteria file
    # old format:
    multiple lines.  pmag_criteria_code defines the type of criteria

    to deal with old format this function reads all the lines and ignore empty cells.
    i.e., the program assumes that in each column there is only one value (in one of the lines)

    special case in the old format:
        specimen_dang has a value and pmag_criteria_code is IE-specimen.
        The program assumes that the user means specimen_int_dang
    # New format for thellier_gui and demag_gui:
    one long line. pmag_criteria_code=ACCEPT

    path is the full path to the criteria file

    the fucntion takes exiting acceptance_criteria
    and updtate it with criteria from file

    output:
    acceptance_criteria={}
    acceptance_criteria[MagIC Variable Names]={}
    acceptance_criteria[MagIC Variable Names]['value']:
        a number for acceptance criteria value
        -999 for N/A
        1/0 for True/False or Good/Bad
    acceptance_criteria[MagIC Variable Names]['threshold_type']:
        "low":  lower cutoff value i.e. crit>=value pass criteria
        "high": high cutoff value i.e. crit<=value pass criteria
        [string1,string2,....]: for flags
    acceptance_criteria[MagIC Variable Names]['decimal_points']:number of decimal points in rounding
            (this is used in displaying criteria in the dialog box)

    '''
    acceptance_criteria_list=acceptance_criteria.keys()
    meas_data,file_type=magic_read(path)
    for rec in meas_data:
        for crit in rec.keys():
            rec[crit]=rec[crit].strip('\n')
            if crit in ['pmag_criteria_code','criteria_definition','magic_experiment_names','er_citation_names']:
                continue
            elif rec[crit]=="":
                continue
            if crit=="specimen_dang" and "pmag_criteria_code" in rec.keys() and "IE-SPEC" in rec["pmag_criteria_code"]:
                crit="specimen_int_dang"
                print "-W- Found backward compatibility problem with selection criteria specimen_dang. Cannot be associated with IE-SPEC. Program assumes that the statistic is specimen_int_dang"
                acceptance_criteria["specimen_int_dang"]['value']=float(rec["specimen_dang"])
            elif crit not in acceptance_criteria_list:
                print "-W- WARNING: criteria code %s is not supported by PmagPy GUI. please check"%crit
                acceptance_criteria[crit]={}
                acceptance_criteria[crit]['value']=rec[crit]
                acceptance_criteria[crit]['threshold_type']="inherited"
                acceptance_criteria[crit]['decimal_points']=-999
                # LJ add:
                acceptance_criteria[crit]['category'] = None

            # bollean flag
            elif acceptance_criteria[crit]['threshold_type']=='bool':
                if str(rec[crit]) in ['1','g','True','TRUE']:
                    acceptance_criteria[crit]['value']=True
                else:
                    acceptance_criteria[crit]['value']=False

            # criteria as flags
            elif type(acceptance_criteria[crit]['threshold_type'])==list:
                if str(rec[crit]) in acceptance_criteria[crit]['threshold_type']:
                    acceptance_criteria[crit]['value']=str(rec[crit])
                else:
                    print "-W- WARNING: data %s from criteria code  %s and is not supported by PmagPy GUI. please check"%(crit,rec[crit])
            elif float(rec[crit]) == -999:
                continue
            else:
                acceptance_criteria[crit]['value']=float(rec[crit])
    return(acceptance_criteria)

def write_criteria_to_file(path,acceptance_criteria):
    crit_list=acceptance_criteria.keys()
    crit_list.sort()
    rec={}
    rec['pmag_criteria_code']="ACCEPT"
    rec['criteria_definition']="acceptance criteria for study"
    rec['er_citation_names']="This study"

    for crit in crit_list:
        # ignore criteria that are not in MagIc model 2.5
        if 'category' in acceptance_criteria[crit].keys():
            if acceptance_criteria[crit]['category']=='thellier_gui':
                continue

        # fix True/False typoes
        if type(acceptance_criteria[crit]['value'])==str:
            if acceptance_criteria[crit]['value']=="TRUE":
                 acceptance_criteria[crit]['value']="True"
            if acceptance_criteria[crit]['value']=="FALSE":
                 acceptance_criteria[crit]['value']="False"

        if type(acceptance_criteria[crit]['value'])==str:
            if acceptance_criteria[crit]['value'] != "-999" and acceptance_criteria[crit]['value'] != "":

                rec[crit]=acceptance_criteria[crit]['value']
        elif type(acceptance_criteria[crit]['value'])==int:
            if acceptance_criteria[crit]['value'] !=-999:
                rec[crit]="%.i"%(acceptance_criteria[crit]['value'])
        elif type(acceptance_criteria[crit]['value'])==float:
            if float(acceptance_criteria[crit]['value'])==-999:
                continue
            decimal_points=acceptance_criteria[crit]['decimal_points']
            if decimal_points != -999:
                command="rec[crit]='%%.%sf'%%(acceptance_criteria[crit]['value'])"%(decimal_points)
                exec command
            else:
                rec[crit]="%e"%(acceptance_criteria[crit]['value'])
        elif type(acceptance_criteria[crit]['value'])==bool:
                rec[crit]=str(acceptance_criteria[crit]['value'])
        else:
            print "-W- WARNING: statistic %s not written to file:",acceptance_criteria[crit]['value']
    magic_write(path,[rec],"pmag_criteria")



def add_flag(var, flag):
    """
    for use when calling command-line scripts from withing a program.
    if a variable is present, add its proper command_line flag.
    return a string.
    """
    if var:
        var = flag + " " + str(var)
    else:
        var = ""
    return var


def get_named_arg_from_sys(name, default_val=None, reqd=False):
    """
    Extract the value after a command-line flag such as '-f' and return it.
    If the command-line flag is missing, return default_val.
    If reqd == True and the command-line flag is missing, throw an error.
    """
    if name in sys.argv: # if the command line flag is found in sys.argv
        ind = sys.argv.index(name)
        return sys.argv[ind+1]
    if reqd: # if arg is required but not present
        raise MissingCommandLineArgException(name)
    return default_val # if arg is not provided but has a default value, return that value

def get_flag_arg_from_sys(name):
    if name in sys.argv:
        return True
    else:
        return False


def merge_recs_headers(recs):
    '''
    take a list of recs [rec1,rec2,rec3....], each rec is a dictionary.
    make sure that all recs have the same headers.
    '''
    headers=[]
    for rec in recs:
        keys=rec.keys()
        for key in keys:
            if key not in headers:
                    headers.append(key)
    for rec in recs:
        for header in headers:
            if header not in rec.keys():
                rec[header]=""
    return recs


def remove_files(file_list, WD='.'):
    for f in file_list:
        full_file = os.path.join(WD, f)
        if os.path.isfile(full_file):
            os.remove(full_file)

def get_attr(obj, attr='name'):
    try:
        name = obj.__getattribute__(attr)
    except AttributeError:
        name = str(obj)
    return name

def adjust_to_360(val, key):
    """
    Take in a value and a key.  If the key is of the type:
    declination/longitude/azimuth/direction, adjust it to be within
    the range 0-360 as required by the MagIC data model
    """
    CheckDec = ['_dec', '_lon', '_azimuth', 'dip_direction']
    adjust = False
    for dec_key in CheckDec:
        if dec_key in key:
            if key.endswith(dec_key) or key.endswith('_'):
                adjust = True
    if not val:
        return ''
    elif not adjust:
        return val
    elif adjust:
        new_val = float(val) % 360
        if new_val != float(val):
            print '-I- adjusted {} {} to 0=>360.: {}'.format(key, val, new_val)
        return new_val


def adjust_all_to_360(dictionary):
    """
    Take a dictionary and check each key/value pair.
    If this key is of type: declination/longitude/azimuth/direction,
    adjust it to be within 0-360 as required by the MagIC data model
    """
    for key in dictionary:
        dictionary[key] = adjust_to_360(dictionary[key], key)
    return dictionary

class MissingCommandLineArgException(Exception):

    def __init__(self, message):
        self.message = "{} is a required option! Please provide this information and try again".format(message)

    def __str__(self):
        return self.message