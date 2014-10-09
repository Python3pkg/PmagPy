#!/usr/bin/env python

import os
import wx
import wx.html


# library for commonly used widgets.  

class choose_file(wx.StaticBoxSizer):

    def __init__(self, parent, orient=wx.VERTICAL, btn_text='add', method=None):
        box = wx.StaticBox( parent, wx.ID_ANY, "" )
        super(choose_file, self).__init__(box, orient=wx.VERTICAL)
        self.btn_text = btn_text
        self.method = method
        self.parent = parent
        self.file_path = wx.TextCtrl(self.parent, id=-1, size=(400,25), style=wx.TE_READONLY)
        self.add_file_button = wx.Button(self.parent, id=-1, label=btn_text,name=btn_text)
        if method:
            self.parent.Bind(wx.EVT_BUTTON, method, self.add_file_button)
        TEXT="Choose file (no spaces are allowed in path):"
        self.Add(wx.StaticText(self.parent, label=TEXT),wx.ALIGN_LEFT)
        self.AddSpacer(4)
        bSizer0_1=wx.BoxSizer(wx.HORIZONTAL)
        bSizer0_1.Add(self.add_file_button, wx.ALIGN_LEFT)
        bSizer0_1.AddSpacer(4)
        bSizer0_1.Add(self.file_path, wx.ALIGN_LEFT)
        self.Add(bSizer0_1, wx.ALIGN_LEFT)

    def return_value(self):
        return self.file_path.GetValue()




class NotEmptyValidator(wx.PyValidator): 
    def __init__(self): 
        print "initing validator"
        wx.PyValidator.__init__(self) 

    def Clone(self): 
        """ 
        Note that every validator must implement the Clone() method. 
        """ 
        print "doing Clone"
        return NotEmptyValidator() 

    def Validate(self, win): 
        print "doing Validate"
        textCtrl = self.GetWindow() 
        text = textCtrl.GetValue() 
        if len(text) == 0: 
            print "textCtrl.Name:", textCtrl.Name
            wx.MessageBox("{} must contain some text!".format(str(textCtrl.Name)), "Error") 
            textCtrl.SetBackgroundColour("pink") 
            textCtrl.SetFocus() 
            textCtrl.Refresh() 
            print "win", win
            return False 
        else:
            textCtrl.SetBackgroundColour( 
                wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)) 
            textCtrl.Refresh() 
            return True 
            
    def TransferToWindow(self): 
        print "doing TransferToWindow"
        return True 

    def TransferFromWindow(self):
        print "doing TransferFromWindow"
        return True


class choose_dir(wx.StaticBoxSizer):
    
    def __init__(self, parent, btn_text='add', method=None):
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(choose_dir, self).__init__(box, orient=wx.VERTICAL)
        self.btn_text = btn_text
        self.parent = parent
        self.parent.dir_path = wx.TextCtrl(parent, id=-1, size=(400,25), style=wx.TE_READONLY)
        self.add_dir_button = wx.Button(parent, id=-1, label=btn_text,name='add')
        if method:
            self.parent.Bind(wx.EVT_BUTTON, method, self.add_dir_button)
        TEXT="Choose folder (no spaces are allowed in path):"
        self.Add(wx.StaticText(self.parent, label=TEXT),wx.ALIGN_LEFT)
        self.AddSpacer(4)
        bSizer0_1=wx.BoxSizer(wx.HORIZONTAL)
        bSizer0_1.Add(self.add_dir_button,wx.ALIGN_LEFT)
        bSizer0_1.AddSpacer(4)
        bSizer0_1.Add(self.parent.dir_path,wx.ALIGN_LEFT)
        self.Add(bSizer0_1,wx.ALIGN_LEFT)

    def return_value(self):
        return self.parent.dir_path.GetValue()


class simple_text(wx.StaticBoxSizer):
    def __init__(self, parent, TEXT):
        self.parent = parent
        box = wx.StaticBox( self.parent, wx.ID_ANY, "" )
        super(simple_text, self).__init__(box, orient=wx.HORIZONTAL)
        self.Add(wx.StaticText(self.parent, label=TEXT),wx.ALIGN_LEFT)
        


class labeled_text_field(wx.StaticBoxSizer):
    def __init__(self, parent, label="User name (optional)"):
        self.parent = parent
        box = wx.StaticBox( self.parent, wx.ID_ANY, "" )
        super(labeled_text_field, self).__init__(box, orient=wx.HORIZONTAL)
        TEXT= label
        self.Add(wx.StaticText(self.parent, label=TEXT),wx.ALIGN_LEFT)
        self.AddSpacer(4)
        self.text_field = wx.TextCtrl(self.parent, id=-1, size=(100,25))
        self.Add(self.text_field,wx.ALIGN_LEFT)
        
    def return_value(self):
        return self.text_field.GetValue()

class labeled_yes_or_no(wx.StaticBoxSizer):
    def __init__(self, parent, TEXT, label1, label2):
        self.parent = parent
        box = wx.StaticBox(self.parent, wx.ID_ANY, "")
        super(labeled_yes_or_no, self).__init__(box, orient=wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.rb1 = wx.RadioButton(parent, label=label1, style=wx.RB_GROUP)
        self.rb1.SetValue(True)
        self.rb2 = wx.RadioButton(parent, label=label2)
        hbox.Add(self.rb1, wx.ALIGN_LEFT)
        hbox.AddSpacer(5)
        hbox.Add(self.rb2, wx.ALIGN_LEFT)
        text = wx.StaticText(self.parent, label=TEXT, style=wx.TE_CENTER)
        self.Add(text, wx.ALIGN_LEFT)
        self.Add(hbox)

    def return_value(self):
        if self.rb1.GetValue():
            return True
        return False


class specimen_n(wx.StaticBoxSizer):
    """-spc option (number of characters defining specimen from sample"""
    def __init__(self, parent, label="number of terminal characters that distinguish specimen from sample"):
        self.parent = parent
        box = wx.StaticBox( self.parent, wx.ID_ANY, "" )
        super(specimen_n, self).__init__(box, orient=wx.HORIZONTAL)
        TEXT= label
        self.Add(wx.StaticText(self.parent, label=TEXT),wx.ALIGN_LEFT)
        self.AddSpacer(4)
        self.spc = wx.SpinCtrl(self.parent, id=-1, size=(100,25),min=0, max=9)
        self.spc.SetValue(0)
        self.Add(self.spc,wx.ALIGN_LEFT)
        
    def return_value(self):
        return self.spc.GetValue()


class select_ncn(wx.StaticBoxSizer):  
    """provides box sizer with a drop down menu for the standard naming conventions"""
    ncn_keys = ['XXXXY', 'XXXX-YY', 'XXXX.YY', 'XXXX[YYY] where YYY is sample designation, enter number of Y', 'sample name=site name', 'Site names in orient.txt file', '[XXXX]YYY where XXXX is the site name, enter number of X', 'this is a synthetic and has no site name']
    def __init__(self, parent, ncn_keys=ncn_keys):
        self.parent = parent
        box = wx.StaticBox( parent, wx.ID_ANY, "" )
        super(select_ncn, self).__init__(box, orient=wx.VERTICAL)
        ncn_values = range(1,9)
        self.sample_naming_conventions = dict(zip(ncn_keys, ncn_values))
        self.select_naming_convention = wx.ComboBox(parent, -1, ncn_keys[0], size=(440,25), choices=ncn_keys, style=wx.CB_READONLY)
        self.sample_naming_convention_char = wx.TextCtrl(parent, id=-1, size=(40,25))
        label1 = wx.StaticText(parent,label="sample-site naming convention:",style=wx.TE_CENTER)
        label2 = wx.StaticText(parent, label="delimiter (if necessary):", style=wx.TE_CENTER)
        gridbSizer = wx.GridBagSizer(5, 10)
        gridbSizer.Add(label1, (0, 0))
        gridbSizer.Add(label2, (0, 1))
        gridbSizer.Add(self.select_naming_convention, (1, 0))
        gridbSizer.Add(self.sample_naming_convention_char, (1, 1))
        self.Add(gridbSizer,wx.ALIGN_LEFT)

    def return_value(self):
        selected_ncn = str(self.select_naming_convention.GetValue())
        ncn_number = self.sample_naming_conventions[selected_ncn]
        if ncn_number == 4 or ncn_number == 7: # these are the only two that require a delimiter
            return str(ncn_number) + '-' + str(self.sample_naming_convention_char.GetValue())
        else:
            return str(ncn_number)


class select_specimen_ocn(wx.StaticBoxSizer):
    def __init__(self, parent):
        self.parent = parent
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(select_specimen_ocn, self).__init__(box, orient=wx.VERTICAL)
        label = wx.StaticText(self.parent, label="Orientation:")
        ocn_keys = ["Lab arrow azimuth= mag_azimuth; Lab arrow dip=-field_dip i.e., field_dip is degrees from vertical down - the hade",
                "Lab arrow azimuth = mag_azimuth-90; Lab arrow dip = -field_dip i.e., mag_azimuth is strike and field_dip is hade",
                "Lab arrow azimuth = mag_azimuth; Lab arrow dip = 90-field_dip i.e.,  lab arrow same as field arrow, but field_dip was a hade.",
                "lab azimuth and dip are same as mag_azimuth, field_dip",
                "lab azimuth is same as mag_azimuth,lab arrow dip=field_dip-90",
                "Lab arrow azimuth = mag_azimuth-90; Lab arrow dip = 90-field_dip"]
        ocn_values = range(1, 6)
        self.sample_orientation_conventions = dict(zip(ocn_keys, ocn_values))
        self.select_orientation_convention = wx.ComboBox(parent, -1, ocn_keys[0], size=(705,25), choices=ocn_keys, style=wx.CB_READONLY)
        self.Add(label, wx.ALIGN_LEFT)
        self.Add(self.select_orientation_convention, wx.ALIGN_LEFT)
        self.AddSpacer(8)

    def return_value(self):
        selected_ocn = str(self.select_orientation_convention.GetValue())
        return self.sample_orientation_conventions[selected_ocn]


class select_declination(wx.StaticBoxSizer):
    def __init__(self, parent):
        self.parent = parent
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(select_declination, self).__init__(box, orient=wx.VERTICAL)
        label1 = wx.StaticText(self.parent, label="Declination:")
        label2 = wx.StaticText(self.parent, label="if necessary")
        self.dec_box = wx.TextCtrl(self.parent, size=(40, 25))
        declination_keys = ["Use the IGRF DEC value at the lat/long and date supplied","Use this DEC: ","DEC=0, mag_az is already corrected in file","Correct mag_az but not bedding_dip_dir"]
        declination_values = range(1, 4)
        self.dcn = dict(zip(declination_keys, declination_values))
        self.select_dcn = wx.ComboBox(parent, -1, declination_keys[0], size=(405, 25), choices=declination_keys, style=wx.CB_READONLY)
        gridSizer = wx.GridSizer(2, 2, 5, 10)
        gridSizer.AddMany( [label1, label2, self.select_dcn, self.dec_box])
        self.Add(gridSizer, wx.ALIGN_LEFT)
        self.AddSpacer(10)
        
        

    def return_value(self):
        selected_dcn = str(self.select_dcn.GetValue())
        dcn_number = self.dcn[selected_dcn]
        if dcn_number == 2:
            return str(dcn_number) + " " + self.dec_box.GetValue()
        else:
            return dcn_number            
        



class replicate_measurements(wx.StaticBoxSizer):
    
    def __init__(self, parent):
        box = wx.StaticBox( parent, wx.ID_ANY, "" )
        super(replicate_measurements, self).__init__(box, orient=wx.HORIZONTAL)
        TEXT="replicate measurements:"
        replicate_text = wx.StaticText(parent,label=TEXT,style=wx.TE_CENTER)
        self.replicate_rb1 = wx.RadioButton(parent, -1, 'Average replicate measurements', style=wx.RB_GROUP)
        self.replicate_rb1.SetValue(True)
        self.replicate_rb2 = wx.RadioButton(parent, -1, 'take only last measurement from replicate measurements')
        self.Add(replicate_text,wx.ALIGN_LEFT)
        self.AddSpacer(8)
        self.Add(self.replicate_rb1,wx.ALIGN_LEFT)
        self.AddSpacer(8)
        self.Add(self.replicate_rb2,wx.ALIGN_LEFT)

    def return_value(self):
        if self.replicate_rb1.GetValue():
            return True
        else:
            return False


class check_box(wx.StaticBoxSizer):
    
    def __init__(self, parent, text):
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(check_box, self).__init__(box, orient=wx.VERTICAL)
        
        self.cb = wx.CheckBox(parent, -1, text)
        self.Add(self.cb, flag=wx.TOP|wx.BOTTOM, border=8)

    def return_value(self):
        return self.cb.GetValue()
        

class radio_buttons(wx.StaticBoxSizer):
    
    def __init__(self, parent, choices):
        box = wx.StaticBox(parent, -1, "")
        super(radio_buttons, self).__init__(box, orient=wx.VERTICAL)
        rb1 = wx.RadioButton(parent, label=choices[0], style=wx.RB_GROUP)
        rb1.SetValue(True)
        self.Add(rb1)
        self.radio_buttons = [rb1]
        for choice in choices[1:]:
            rb = wx.RadioButton(parent, label=choice)
            self.Add(rb)
            self.radio_buttons.append(rb)

    def return_value(self):
        for rb in self.radio_buttons:
            val = rb.GetValue()
            if val:
                return rb.Label


class large_checkbox_window(wx.StaticBoxSizer):

    def __init__(self, parent, choices, text):
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(large_checkbox_window, self).__init__(box, orient=wx.VERTICAL)
        
        self.gridSizer = wx.FlexGridSizer(23, 10, 9, 10)
        labels = [wx.StaticText(parent, label=choice) for choice in sorted(choices)]
        for label in labels:
            self.gridSizer.Add(label, flag=wx.ALIGN_RIGHT)
            text_control = wx.TextCtrl(parent)
            text_sizer = self.gridSizer.Add(text_control)
            if choices[label.Label]:
                text_control.SetValue(choices[label.Label])
        self.Add(self.gridSizer, wx.ALIGN_LEFT)

    def return_value(self):
        keys = []
        values = []
        for sizer in self.gridSizer.Children:
            if isinstance(sizer.GetWindow(), wx._controls.TextCtrl):
                values.append(str(sizer.GetWindow().GetValue())) 
            else:
                keys.append(str(sizer.GetWindow().Label))
        data_dict = dict(zip(keys, values))
        return [data_dict]



class check_boxes(wx.StaticBoxSizer):
    
    def __init__(self, parent, gridsize, choices, text):
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(check_boxes, self).__init__(box, orient=wx.VERTICAL)
        
        gridSizer2 = wx.GridSizer(gridsize[0], gridsize[1], gridsize[2], gridsize[3])
        self.boxes = []
        for n, choice in enumerate(choices):
            cb = wx.CheckBox(parent, -1, choice)
            self.boxes.append(cb)
            gridSizer2.Add(cb, wx.ALIGN_RIGHT)
        self.Add(wx.StaticText(parent, label = text), wx.ALIGN_LEFT)
        self.Add(gridSizer2, wx.ALIGN_RIGHT)
        self.AddSpacer(4)

    def return_value(self):
        checked = []
        for cb in self.boxes:
            if cb.GetValue():
                checked.append(str(cb.Label))
        return checked



class sampling_particulars(check_boxes):

    def __init__(self, parent):
        gridsize = (5, 2, 0, 0)
        TEXT = "Sampling Particulars (select all that apply):"
        particulars = ["FS-FD: field sampling done with a drill", "FS-H: field sampling done with hand samples", "FS-LOC-GPS: field location done with GPS", "FS-LOC-MAP:  field location done with map", "SO-POM:  a Pomeroy orientation device was used", "SO-ASC:  an ASC orientation device was used", "SO-MAG: magnetic compass used for all orientations", "SO-SUN: sun compass used for all orientations", "SO-SM: either magnetic or sun used on all orientations", "SO-SIGHT: orientation from sighting"]
        super(sampling_particulars, self).__init__(parent, gridsize, particulars, TEXT)

    def return_value(self):
        checked = super(sampling_particulars, self).return_value()
        particulars = [p.split(':')[0] for p in checked]
        particulars = ':'.join(particulars)
        return particulars


class lab_field(wx.StaticBoxSizer):
    
    def __init__(self, parent):
        box = wx.StaticBox( parent, wx.ID_ANY, "", size=(100,100))
        super(lab_field, self).__init__(box, orient=wx.VERTICAL)
        TEXT="Lab field (leave blank if unnecessary). Example: 40 0 -90"
        self.file_info_text = wx.StaticText(parent,label=TEXT,style=wx.TE_CENTER)
        self.file_info_Blab = wx.TextCtrl(parent, id=-1, size=(40,25))
        self.file_info_Blab_dec = wx.TextCtrl(parent, id=-1, size=(40,25))
        self.file_info_Blab_inc = wx.TextCtrl(parent, id=-1, size=(40,25))
        gridbSizer3 = wx.GridSizer(2, 3, 0, 10)
        gridbSizer3.AddMany( [(wx.StaticText(parent,label="B (uT)",style=wx.TE_CENTER),wx.ALIGN_LEFT),
            (wx.StaticText(parent,label="dec",style=wx.TE_CENTER),wx.ALIGN_LEFT),
            (wx.StaticText(parent,label="inc",style=wx.TE_CENTER),wx.ALIGN_LEFT),
            (self.file_info_Blab,wx.ALIGN_LEFT),
            (self.file_info_Blab_dec,wx.ALIGN_LEFT),
            (self.file_info_Blab_inc,wx.ALIGN_LEFT)])
        self.Add(self.file_info_text,wx.ALIGN_LEFT)
        self.AddSpacer(8)
        self.Add(gridbSizer3,wx.ALIGN_LEFT)

    def return_value(self):
        lab_field = "{} {} {}".format(self.file_info_Blab.GetValue(), self.file_info_Blab_dec.GetValue(), self.file_info_Blab_inc.GetValue())
        if lab_field.isspace():
            return ''
        return lab_field


class synthetic(wx.StaticBoxSizer):
    def __init__(self, parent):
        box = wx.StaticBox(parent, wx.ID_ANY, "if synthetic:")
        super(synthetic, self).__init__(box, orient=wx.VERTICAL)
        gridSizer = wx.GridSizer(2, 2, 3, 10)
        institution_text = wx.StaticText(parent,label="Institution (no spaces)", style=wx.TE_CENTER)
        self.institution_field = wx.TextCtrl(parent, id=-1, size=(200, 25))
        type_text = wx.StaticText(parent, label="Type (no spaces)", style=wx.TE_CENTER)
        self.type_field = wx.TextCtrl(parent, id=-1, size=(200, 25))
        gridSizer.AddMany([(institution_text, wx.ALIGN_LEFT),
                           (type_text, wx.ALIGN_LEFT), 
                           (self.institution_field, wx.ALIGN_LEFT),
                           (self.type_field, wx.ALIGN_LEFT)])
        self.Add(gridSizer)

    def return_value(self):
        if self.institution_field.GetValue():
            return str(self.institution_field.GetValue()) + ' ' + str(self.type_field.GetValue())
                                        



class experiment_type(wx.StaticBoxSizer):
    
    def __init__(self, parent):
        box = wx.StaticBox(parent, wx.ID_ANY, "")
        super(experiment_type, self).__init__(box, orient=wx.VERTICAL)
        gridSizer2 = wx.GridSizer(5, 3, 0, 0)
        self.boxes = []
        experiment_names=['AF Demag', 'Thermal (includes thellier but not trm)', 'Shaw method', 'IRM (acquisition)', '3D IRM experiment', 'NRM only', 'TRM acquisition', 'double AF demag', 'triple AF demag (GRM protocol)', 'Cooling rate experiment']
        TEXT = "Experiment type (select all that apply):"
        for n, experiment in enumerate(experiment_names):
            cb = wx.CheckBox(parent, -1, experiment)
            self.boxes.append(cb)
            gridSizer2.Add(cb, wx.ALIGN_RIGHT)
        self.Add(wx.StaticText(parent, label = TEXT), wx.ALIGN_LEFT)
        self.Add(gridSizer2, wx.ALIGN_RIGHT)
        self.AddSpacer(4)

    def return_value(self):
        checked = []
        for cb in self.boxes:
            if cb.GetValue():
                checked.append(str(cb.Label))
        if not checked:
            return ''
        experiment_key = {'AF Demag': 'AF', 'Thermal (includes thellier but not trm)': 'T', 'Shaw method': 'S', 'IRM (acquisition)': 'I', '3D IRM experiment': 'I3d', 'NRM only': 'N', 'TRM acquisition': 'TRM', 'anisotropy experiment': 'ANI', 'double AF demag': 'D', 'triple AF demag (GRM protocol)': 'G', 'Cooling rate experiment': 'CR'}
        experiment_string = ''
        for ex in checked:
            experiment_string += experiment_key[ex] + ':'
        return experiment_string[:-1]
    

class btn_panel(wx.BoxSizer):

    def __init__(self, SELF, panel):
        super(btn_panel, self).__init__(wx.HORIZONTAL)
        pnl = panel
        SELF.okButton = wx.Button(pnl, wx.ID_OK, "&OK")
        SELF.Bind(wx.EVT_BUTTON, SELF.on_okButton, SELF.okButton)

        SELF.cancelButton = wx.Button(pnl, wx.ID_CANCEL, '&Cancel')
        SELF.Bind(wx.EVT_BUTTON, SELF.on_cancelButton, SELF.cancelButton)

        SELF.helpButton = wx.Button(pnl, wx.ID_ANY, '&Help')
        SELF.Bind(wx.EVT_BUTTON, SELF.on_helpButton, SELF.helpButton)

        self.Add(SELF.okButton, 0, wx.ALL, 5)
        self.Add(SELF.cancelButton, 0, wx.ALL, 5 )
        self.Add(SELF.helpButton, 0, wx.ALL, 5)


class combine_files(wx.BoxSizer):
    
    def __init__(self, parent, text):
        super(combine_files, self).__init__(wx.VERTICAL)
        self.parent = parent
        self.WD = self.parent.WD
        self.text = text

        bSizer0a =  wx.StaticBoxSizer( wx.StaticBox( self.parent.panel, wx.ID_ANY, "" ), wx.HORIZONTAL )
        self.add_file_button = wx.Button(self.parent.panel, id=-1, label='add file',name='add')
        self.parent.Bind(wx.EVT_BUTTON, self.on_add_file_button, self.add_file_button)    
        self.add_all_files_button = wx.Button(self.parent.panel, id=-1, label="add all *_" + text + " files",name='add_all')
        self.parent.Bind(wx.EVT_BUTTON, self.on_add_all_files_button, self.add_all_files_button)    
        bSizer0a.AddSpacer(5)
        bSizer0a.Add(self.add_file_button,wx.ALIGN_LEFT)
        bSizer0a.AddSpacer(5)
        bSizer0a.Add(self.add_all_files_button,wx.ALIGN_LEFT)
        bSizer0a.AddSpacer(5)
                
        bSizer0b =  wx.StaticBoxSizer( wx.StaticBox( self.parent.panel, wx.ID_ANY, "" ), wx.VERTICAL )
        self.file_paths = wx.TextCtrl(self.parent.panel, id=-1, size=(400,200), style=wx.TE_MULTILINE)
        TEXT="files list:"
        bSizer0b.AddSpacer(5)
        bSizer0b.Add(wx.StaticText(self.parent.panel,label=TEXT),wx.ALIGN_LEFT)        
        bSizer0b.AddSpacer(5)
        bSizer0b.Add(self.file_paths,wx.ALIGN_LEFT)
        bSizer0b.AddSpacer(5)
        bSizer0b.Add(wx.StaticText(self.parent.panel, label="Will combine into one {} file".format(text)), wx.ALIGN_LEFT)

        self.Add(bSizer0a, wx.ALIGN_LEFT)
        self.Add(bSizer0b, wx.ALIGN_LEFT)

    def on_add_file_button(self,event):

        dlg = wx.FileDialog(
            None,message="choose MagIC formatted measurement file",
            defaultDir=self.WD,
            defaultFile="",
            style=wx.OPEN | wx.CHANGE_DIR 
            )
        if dlg.ShowModal() == wx.ID_OK:
            full_path = dlg.GetPath()
            infile = full_path[full_path.rfind('/')+1:]
            self.file_paths.AppendText(infile + "\n")

    def on_add_all_files_button(self,event):
        all_files=os.listdir(self.WD)
        for F in all_files:
            F=str(F)
            if len(F)>6:
                if self.text in F:
                    if "#" not in F and "~" not in F and not F.endswith('.pyc'): # prevents binary files from going into the mix, as well as misc saved stuff
                        self.file_paths.AppendText(F+"\n")


# NEED TO MAKE THIS ABLE TO FIND HTML FILES IN USER's path.  sigh.
class LinkEnabledHtmlWindow(wx.html.HtmlWindow):
    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())

class HtmlFrame(wx.Frame):
    """ This window displays a HtmlWindow """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, None, wx.ID_ANY, title="Help Window", size=(600,400))
        page = kwargs.get('page', 'http://earthref.org/MAGIC/shortlists/')
        htmlwin = LinkEnabledHtmlWindow(self)
        htmlwin.LoadPage(page)
        htmlwin.Fit()

 
        
class AddItem(wx.Frame):
    """This window allows user to add a new item (sample or specimen)"""

    def __init__(self, parent, title, belongs_to, owner_items, data_method): 
        self.title = title
        self.owner_items = owner_items
        self.belongs_to = belongs_to
        self.onAdd = data_method# data parsing method passed in by pmag_basic_dialogs
        wx.Frame.__init__(self, parent, wx.ID_ANY, title=self.title)
        self.InitUI()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.item_name = labeled_text_field(panel, label="{} Name: ".format(self.title))
        owner_box = wx.StaticBox(panel, wx.ID_ANY, "" )
        owner_boxSizer = wx.StaticBoxSizer(owner_box)
        items = self.owner_items
        owner_label = wx.StaticText(panel, label="Belongs to {}: ".format(self.belongs_to), style=wx.TE_CENTER)
        self.owner_name = wx.ComboBox(panel, -1, items[0], choices=items, style=wx.CB_READONLY)
        owner_boxSizer.Add(owner_label, flag=wx.RIGHT, border=5)
        owner_boxSizer.Add(self.owner_name)
        vbox.Add(self.item_name)
        vbox.Add(owner_boxSizer)
        btn_panel = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(panel, wx.ID_ANY, '&Add {}'.format(self.title))
        cancelButton = wx.Button(panel, wx.ID_ANY, '&Cancel')
        self.Bind(wx.EVT_BUTTON, self.on_okButton, okButton)
        self.Bind(wx.EVT_BUTTON, self.on_cancelButton, cancelButton)
        btn_panel.AddMany([okButton, cancelButton])
        vbox.Add(btn_panel)
        vbox.AddSpacer(10)

        panel.SetSizer(vbox)
        vbox.Fit(self)
        self.Show()

    def on_cancelButton(self, event):
        self.Destroy()
        
    def on_okButton(self, event):
        print "doing on_okButton"
        item = str(self.item_name.return_value())
        owner = str(self.owner_name.GetValue())
        self.onAdd(item, owner)
        self.Destroy()
        


# methods!


def on_add_dir_button(SELF, WD, event, text):
    dlg = wx.DirDialog(
            None, message=text,
            defaultPath=".",
        style=wx.OPEN | wx.DD_DEFAULT_STYLE
            )
    if dlg.ShowModal() == wx.ID_OK:
        SELF.dir_path.SetValue(str(dlg.GetPath()))


def on_add_file_button(SELF, WD, event, text):
    dlg = wx.FileDialog(
            None, message=text,
        defaultDir=WD,
            defaultFile="",
        style=wx.OPEN | wx.CHANGE_DIR
            )
    if dlg.ShowModal() == wx.ID_OK:
        SELF.file_path.SetValue(str(dlg.GetPath()))


def simple_warning(text):
    dlg = wx.MessageDialog(None, message=text, caption="warning", style=wx.ICON_ERROR|wx.OK)
    dlg.ShowModal()
    dlg.Destroy()
    

def on_helpButton(command=None, text=None):
    import subprocess
    if text:
        result = text
    else:
        result = subprocess.check_output(command, shell=True)
    dlg = wx.Dialog(None, title="help")
    text = wx.TextCtrl(dlg, -1, result, size=(620,540), style=wx.TE_MULTILINE | wx.TE_READONLY)
    sizer = wx.BoxSizer(wx.VERTICAL)
    btnsizer = wx.BoxSizer()
    btn = wx.Button(dlg, wx.ID_OK)
    btnsizer.Add(btn, 0, wx.ALL, 5)
    btnsizer.Add((5,-1), 0, wx.ALL, 5)
    sizer.Add(text, 0, wx.EXPAND|wx.ALL, 5)    
    sizer.Add(btnsizer, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)    
    dlg.SetSizerAndFit(sizer)
    dlg.Centre()
    dlg.ShowModal()
    dlg.Destroy()




def run_command(SELF, command, outfile):
    print "-I- Running Python command:\n %s"%command
    os.system(command)
    print "-I- Saved results in MagIC format file: {}".format(outfile)


def run_command_and_close_window(SELF, command, outfile):
    print "-I- Running Python command:\n %s"%command
    os.system(command)
    if not outfile:
        outfile = ''
    MSG="file(s) converted to MagIC format file:\n%s.\n\n See Termimal (Mac) or command prompt (windows) for errors"% outfile
    dlg = wx.MessageDialog(None,caption="Message:", message=MSG ,style=wx.OK|wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
    SELF.Destroy()
    SELF.Parent.Raise()


