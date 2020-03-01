"""
New wallpaper configuration GUI for Superpaper.
"""
import os
from operator import itemgetter
from PIL import Image, ImageEnhance

import superpaper.sp_logging as sp_logging
import superpaper.wallpaper_processing as wpproc
from superpaper.configuration_dialogs import BrowsePaths, HelpFrame
from superpaper.data import GeneralSettingsData, ProfileData, TempProfileData, CLIProfileData, list_profiles
from superpaper.message_dialog import show_message_dialog
from superpaper.sp_paths import PATH, CONFIG_PATH, PROFILES_PATH
from superpaper.wallpaper_processing import NUM_DISPLAYS, get_display_data, change_wallpaper_job, resize_to_fill

try:
    import wx
    import wx.adv
except ImportError:
    exit()

RESOURCES_PATH = os.path.join(PATH, "superpaper/resources")
TRAY_ICON = os.path.join(RESOURCES_PATH, "superpaper.png")

class ConfigFrame(wx.Frame):
    """Wallpaper configuration dialog frame base class."""
    def __init__(self, parent_tray_obj):
        wx.Frame.__init__(self, parent=None, title="Superpaper Wallpaper Configuration")
        self.frame_sizer = wx.BoxSizer(wx.VERTICAL)
        config_panel = WallpaperSettingsPanel(self, parent_tray_obj)
        self.frame_sizer.Add(config_panel, 1, wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(self.frame_sizer)
        self.SetMinSize((600,600))
        self.SetIcon(wx.Icon(TRAY_ICON, wx.BITMAP_TYPE_PNG))
        self.Fit()
        self.Layout()
        self.Center()
        self.Show()

class WallpaperSettingsPanel(wx.Panel):
    """This class defines the wallpaper config dialog UI."""
    def __init__(self, parent, parent_tray_obj):
        wx.Panel.__init__(self, parent)
        self.frame = parent
        self.parent_tray_obj = parent_tray_obj
        self.sizer_main = wx.BoxSizer(wx.VERTICAL)
        self.sizer_top_half = wx.BoxSizer(wx.HORIZONTAL) # wallpaper/monitor preview
        self.sizer_bottom_half = wx.BoxSizer(wx.VERTICAL) # settings, buttons etc
        # bottom_half: setting sizers
        self.sizer_profiles = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_setting_sizers = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_settings_left = wx.BoxSizer(wx.VERTICAL)
        self.sizer_settings_right = wx.BoxSizer(wx.HORIZONTAL)
        # bottom_half: bottom button row
        self.sizer_bottom_buttonrow = wx.BoxSizer(wx.HORIZONTAL)

        self.defdir = GeneralSettingsData().browse_default_dir
        # settings GUI properties
        self.tc_width = 160  # standard width for wx.TextCtrl etc elements.
        self.show_advanced_settings = False
        self.use_multi_image = False
        BMP_SIZE = 32
        self.tsize = (BMP_SIZE, BMP_SIZE)
        self.image_list = wx.ImageList(BMP_SIZE, BMP_SIZE)

        # top half
        self.resized = False
        # display_data = wpproc.get_display_data()
        self.display_sys = wpproc.DisplaySystem()
        # self.wpprev_pnl = WallpaperPreviewPanel(self.frame, self.display_sys)
        self.wpprev_pnl = WallpaperPreviewPanel(self, self.display_sys)
        self.sizer_top_half.Add(self.wpprev_pnl, 1, wx.CENTER|wx.EXPAND, 5)
        # self.sizer_top_half.SetMinSize((400,200))
        # self.sizer_top_half.SetMinSize()
        self.wpprev_pnl.Bind(wx.EVT_SIZE, self.onResize)
        self.wpprev_pnl.Bind(wx.EVT_IDLE, self.onIdle)
        
        # bottom half
        
        # profile sizer contents
        self.create_sizer_profiles()

        # settings sizer left contents
        self.create_sizer_settings_left()

        self.create_sizer_settings_advanced()

        # settings sizer right contents
        self.create_sizer_settings_right()

        # bottom button row contents
        self.create_sizer_bottom_buttonrow()


        # Add sub-sizers to bottom_half
        #    Note: horizontal sizer needs children to have proportion = 1
        #    in order to expand them horizontally instead of vertically.
        self.sizer_setting_sizers.Add(self.sizer_settings_left, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_sizers.Add(self.sizer_setting_adv, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_sizers.Layout()
        self.sizer_setting_sizers.Add(self.sizer_settings_right, 1, wx.CENTER|wx.EXPAND|wx.ALL, 0)

        self.sizer_bottom_half.Add(self.sizer_profiles, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_bottom_half.Add(self.sizer_setting_sizers, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_bottom_half.Add(self.sizer_bottom_buttonrow, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_bottom_half.SetMinSize(1000,500)

        # Collect items at main sizer
        self.sizer_main.Add(self.sizer_top_half, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_main.Add(self.sizer_bottom_half, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.sizer_main)
        self.sizer_main.Fit(parent)

        self.sizer_setting_sizers.Hide(self.sizer_setting_adv)

        ### End __init__.



    #
    # Sizer creation methods
    #
    def create_sizer_profiles(self):
        # choice menu
        self.list_of_profiles = list_profiles()
        self.profnames = []
        for prof in self.list_of_profiles:
            self.profnames.append(prof.name)
        self.profnames.append("Create a new profile")
        self.choice_profiles = wx.Choice(self, -1, name="ProfileChoice", choices=self.profnames)
        self.choice_profiles.Bind(wx.EVT_CHOICE, self.onSelect)
        st_choice_profiles = wx.StaticText(self, -1, "Setting profiles:")
        # name txt ctrl
        st_name = wx.StaticText(self, -1, "Profile name:")
        self.tc_name = wx.TextCtrl(self, -1, size=(self.tc_width, -1))
        # buttons
        self.button_new = wx.Button(self, label="New")
        self.button_save = wx.Button(self, label="Save")
        self.button_delete = wx.Button(self, label="Delete")
        self.button_new.Bind(wx.EVT_BUTTON, self.onCreateNewProfile)
        self.button_save.Bind(wx.EVT_BUTTON, self.onSave)
        self.button_delete.Bind(wx.EVT_BUTTON, self.onDeleteProfile)

        # Add elements to the sizer
        self.sizer_profiles.Add(st_choice_profiles, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(self.choice_profiles, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(st_name, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(self.tc_name, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(self.button_new, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(self.button_save, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_profiles.Add(self.button_delete, 0, wx.CENTER|wx.ALL, 5)


    def create_sizer_settings_left(self):
        # span mode sizer
        radio_choices_spanmode = ["Simple span", "Advanced span", "Separate image for every display"]
        self.radiobox_spanmode = wx.RadioBox(
            self, wx.ID_ANY,
            label="Span mode",
            choices=radio_choices_spanmode,
            style=wx.RA_VERTICAL
        )
        self.radiobox_spanmode.Bind(wx.EVT_RADIOBOX, self.onSpanRadio)

        # slideshow sizer
        self.sizer_setting_slideshow = wx.StaticBoxSizer(wx.VERTICAL, self, "Wallpaper Slideshow")
        statbox_parent_sshow = self.sizer_setting_slideshow.GetStaticBox()
        self.st_sshow_sort = wx.StaticText(statbox_parent_sshow, -1, "Slideshow order:")
        self.ch_sshow_sort = wx.Choice(statbox_parent_sshow, -1, name="SortChoice",
                                 size=(self.tc_width, -1),
                                 choices=["Shuffle", "Alphabetical"])
        self.st_sshow_delay = wx.StaticText(statbox_parent_sshow, -1, "Delay (minutes):")
        self.tc_sshow_delay = wx.TextCtrl(
            statbox_parent_sshow, -1,
            size=(self.tc_width, -1),
            style=wx.TE_RIGHT
        )
        self.cb_slideshow = wx.CheckBox(statbox_parent_sshow, -1, "Slideshow")
        self.st_sshow_sort.Disable()
        self.st_sshow_delay.Disable()
        self.tc_sshow_delay.Disable()
        self.ch_sshow_sort.Disable()
        self.cb_slideshow.Bind(wx.EVT_CHECKBOX, self.onCheckboxSlideshow)
        self.sizer_setting_slideshow.Add(self.cb_slideshow, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_slideshow.Add(self.st_sshow_delay, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_slideshow.Add(self.tc_sshow_delay, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_slideshow.Add(self.st_sshow_sort, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_slideshow.Add(self.ch_sshow_sort, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # hotkey sizer
        self.sizer_setting_hotkey = wx.StaticBoxSizer(wx.VERTICAL, self, "Hotkey")
        statbox_parent_hkey = self.sizer_setting_hotkey.GetStaticBox()
        self.cb_hotkey = wx.CheckBox(statbox_parent_hkey, -1, "Bind a hotkey to this profile")
        st_hotkey_bind = wx.StaticText(statbox_parent_hkey, -1, "Hotkey to bind:")
        st_hotkey_bind.Disable()
        self.tc_hotkey_bind = wx.TextCtrl(statbox_parent_hkey, -1, size=(self.tc_width, -1))
        self.tc_hotkey_bind.Disable()
        self.hotkey_bind_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hotkey_bind_sizer.Add(st_hotkey_bind, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.hotkey_bind_sizer.Add(self.tc_hotkey_bind, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_hotkey.Add(self.cb_hotkey, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_hotkey.Add(self.hotkey_bind_sizer, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.cb_hotkey.Bind(wx.EVT_CHECKBOX, self.onCheckboxHotkey)

        # Add subsizers to the left column sizer
        self.sizer_settings_left.Add(self.radiobox_spanmode, 0, wx.CENTER|wx.EXPAND, 5)
        self.sizer_settings_left.Add(self.sizer_setting_slideshow, 0, wx.CENTER|wx.EXPAND, 5)
        self.sizer_settings_left.Add(self.sizer_setting_hotkey, 0, wx.CENTER|wx.EXPAND, 5)


    def create_sizer_settings_right(self):
        # paths sizer contents
        self.create_sizer_paths()

    def create_sizer_paths(self):
        self.sizer_setting_paths = wx.StaticBoxSizer(wx.VERTICAL, self, "Wallpaper Paths")
        self.statbox_parent_paths = self.sizer_setting_paths.GetStaticBox()
        st_paths_info = wx.StaticText(self.statbox_parent_paths, -1, "Browse to add your wallpaper files or source folders here:")
        if self.use_multi_image:
            self.path_listctrl = wx.ListCtrl(self.statbox_parent_paths, -1,
                                              style=wx.LC_REPORT
                                              | wx.BORDER_SIMPLE
                                              | wx.LC_SORT_ASCENDING
                                             )
            self.path_listctrl.InsertColumn(0, 'Display', wx.LIST_FORMAT_RIGHT, width = 100)
            self.path_listctrl.InsertColumn(1, 'Source', width = 400)
        else:
            # show simpler listing without header if only one wallpaper target
            self.path_listctrl = wx.ListCtrl(self.statbox_parent_paths, -1,
                                              style=wx.LC_REPORT
                                              | wx.BORDER_SIMPLE
                                              | wx.LC_NO_HEADER
                                             )
            self.path_listctrl.InsertColumn(0, 'Source', width = 500)
        self.path_listctrl.SetImageList(self.image_list, wx.IMAGE_LIST_SMALL)

        self.sizer_setting_paths.Add(st_paths_info, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_paths.Add(self.path_listctrl, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        # Buttons
        self.sizer_setting_paths_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.button_browse = wx.Button(self.statbox_parent_paths, label="Browse")
        self.button_remove_source = wx.Button(self.statbox_parent_paths, label="Remove selected source")
        self.button_browse.Bind(wx.EVT_BUTTON, self.onBrowsePaths)
        self.button_remove_source.Bind(wx.EVT_BUTTON, self.onRemoveSource)
        self.sizer_setting_paths_buttons.Add(self.button_browse, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_setting_paths_buttons.Add(self.button_remove_source, 0, wx.CENTER|wx.ALL, 5)
        # add button sizer to parent paths sizer
        self.sizer_setting_paths.Add(self.sizer_setting_paths_buttons, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)

        self.sizer_settings_right.Add(self.sizer_setting_paths, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)


    def create_sizer_settings_advanced(self):
        """Create sizer for advanced spanning settings."""
        self.sizer_setting_adv = wx.StaticBoxSizer(wx.VERTICAL, self, "Advanced Wallpaper Adjustment")
        statbox_parent_adv = self.sizer_setting_adv.GetStaticBox()

        # Fallback Diagonal Inches
        self.sizer_setting_diaginch = wx.StaticBoxSizer(wx.VERTICAL, self, "Display Diagonal Sizes")
        statbox_parent_diaginch = self.sizer_setting_diaginch.GetStaticBox()
        st_diaginch_override = wx.StaticText(
            statbox_parent_diaginch, -1,
            "Manual display size input:"
        )
        self.button_override = wx.Button(statbox_parent_diaginch, label="Override detected sizes")
        self.button_override.Bind(wx.EVT_BUTTON, self.onOverrideSizes)
        self.sizer_setting_diaginch.Add(st_diaginch_override, 0, wx.CENTER|wx.ALL, 5)
        self.sizer_setting_diaginch.Add(self.button_override, 0, wx.CENTER|wx.BOTTOM, 20)

        # Bezels
        self.sizer_setting_bezels = wx.StaticBoxSizer(wx.VERTICAL, self, "Bezel Correction")
        statbox_parent_bezels = self.sizer_setting_bezels.GetStaticBox()
        # self.cb_bezels = wx.CheckBox(statbox_parent_bezels, -1, "Apply bezel correction")
        # self.cb_bezels.Bind(wx.EVT_CHECKBOX, self.onCheckboxBezels)
        # self.sizer_setting_bezels.Add(self.cb_bezels, 0, wx.ALIGN_LEFT|wx.LEFT, 5)

        self.sizer_bezel_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.button_bezels = wx.Button(statbox_parent_bezels, -1, label="Configure bezels")
        self.button_bezels_save = wx.Button(statbox_parent_bezels, -1, label="Save bezels")
        self.button_bezels_canc = wx.Button(statbox_parent_bezels, -1, label="Cancel")
        self.button_bezels.Bind(wx.EVT_BUTTON, self.onConfigureBezels)
        self.button_bezels_save.Bind(wx.EVT_BUTTON, self.onConfigureBezelsSave)
        self.button_bezels_canc.Bind(wx.EVT_BUTTON, self.onConfigureBezelsCanc)
        self.sizer_bezel_buttons.Add(self.button_bezels, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.sizer_bezel_buttons.Add(self.button_bezels_save, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.sizer_bezel_buttons.Add(self.button_bezels_canc, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.sizer_setting_bezels.Add(self.sizer_bezel_buttons, 0, wx.EXPAND, 0)
        # self.button_bezels.Disable()

        # Offsets
        self.sizer_setting_offsets = wx.StaticBoxSizer(wx.VERTICAL, self, "Manual Display Offsets")
        statbox_parent_offsets = self.sizer_setting_offsets.GetStaticBox()
        self.cb_offsets = wx.CheckBox(statbox_parent_offsets, -1, "Apply manual offsets")
        self.cb_offsets.Bind(wx.EVT_CHECKBOX, self.onCheckboxOffsets)
        st_offsets = wx.StaticText(
            statbox_parent_offsets, -1,
            "Manual wallpaper offsets/panning in pixels (x,y=px,px):"
        )
        st_offsets.Disable()
        self.sizer_setting_offsets.Add(self.cb_offsets, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_setting_offsets.Add(st_offsets, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        tc_list_sizer_offs = wx.BoxSizer(wx.HORIZONTAL)
        self.tc_list_offsets = self.list_of_textctrl(statbox_parent_offsets, wpproc.NUM_DISPLAYS)
        for tc in self.tc_list_offsets:
            tc_list_sizer_offs.Add(tc, 0, wx.ALIGN_LEFT|wx.ALL, 5)
            tc.SetValue("0,0")
            tc.Disable()
        self.sizer_setting_offsets.Add(tc_list_sizer_offs, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        # Add setting subsizers to the adv settings sizer
        self.sizer_setting_adv.Add(self.sizer_setting_diaginch, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_adv.Add(self.sizer_setting_bezels, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.sizer_setting_adv.Add(self.sizer_setting_offsets, 0, wx.CENTER|wx.EXPAND|wx.ALL, 5)


    def create_sizer_diaginch_override(self):
        self.sizer_setting_diaginch.Clear(True)
        statbox_parent_diaginch = self.sizer_setting_diaginch.GetStaticBox()
        self.cb_diaginch = wx.CheckBox(statbox_parent_diaginch, -1, "Input display sizes manually")
        self.cb_diaginch.Bind(wx.EVT_CHECKBOX, self.onCheckboxDiaginch)
        st_diaginch = wx.StaticText(
            statbox_parent_diaginch, -1,
            "Display diagonal sizes (inches):"
        )
        st_diaginch.Disable()
        self.sizer_setting_diaginch.Add(self.cb_diaginch, 0, wx.ALIGN_LEFT|wx.LEFT, 5)
        self.sizer_setting_diaginch.Add(st_diaginch, 0, wx.ALIGN_LEFT|wx.LEFT, 5)
        # diag size data for fields
        diags = [str(dsp.diagonal_size()[1]) for dsp in self.display_sys.disp_list]
        # sizer for textctrls
        tc_list_sizer_diag = wx.BoxSizer(wx.HORIZONTAL)
        self.tc_list_diaginch = self.list_of_textctrl(statbox_parent_diaginch, wpproc.NUM_DISPLAYS)
        for tc, diag in zip(self.tc_list_diaginch, diags):
            tc_list_sizer_diag.Add(tc, 0, wx.ALIGN_LEFT|wx.ALL, 5)
            tc.ChangeValue(diag)
            tc.Disable()
        self.button_diaginch_save = wx.Button(statbox_parent_diaginch, label="Save")
        self.button_diaginch_save.Bind(wx.EVT_BUTTON, self.onSaveDiagInch)
        tc_list_sizer_diag.Add(self.button_diaginch_save, 0, wx.ALL, 5)
        self.button_diaginch_save.Disable()
        self.sizer_setting_diaginch.Add(tc_list_sizer_diag, 0, wx.ALIGN_LEFT|wx.ALL, 0)
        self.sizer_setting_adv.Layout()
        self.sizer_main.Fit(self.frame)
        # Check cb according to DisplaySystem 'use_user_diags'
        self.cb_diaginch.SetValue(self.display_sys.use_user_diags)
        # Update sizer content based on new cb state
        self.onCheckboxDiaginch(None)

    def create_sizer_bottom_buttonrow(self):
        self.button_help = wx.Button(self, label="Help")
        self.button_align_test = wx.Button(self, label="Align Test")
        self.button_apply = wx.Button(self, label="Apply")
        self.button_close = wx.Button(self, label="Close")

        self.button_apply.Bind(wx.EVT_BUTTON, self.onApply)
        self.button_align_test.Bind(wx.EVT_BUTTON, self.onAlignTest)
        self.button_help.Bind(wx.EVT_BUTTON, self.onHelp)
        self.button_close.Bind(wx.EVT_BUTTON, self.onClose)

        self.sizer_bottom_buttonrow.Add(self.button_help, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_bottom_buttonrow.Add(self.button_align_test, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.sizer_bottom_buttonrow.Hide(self.button_align_test)
        self.sizer_bottom_buttonrow.Layout()
        self.sizer_bottom_buttonrow.AddStretchSpacer()
        self.sizer_bottom_buttonrow.Add(self.button_apply, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.sizer_bottom_buttonrow.Add(self.button_close, 0, wx.ALIGN_RIGHT|wx.ALL, 5)



    #
    # Profile loading and display methods
    #
    def populate_fields(self, profile):
        """Populates config dialog fields with data from a profile."""
        self.tc_name.ChangeValue(profile.name)

        self.show_advanced_settings = False
        self.use_multi_image = False
        legacy_advanced = bool(
            profile.spanmode == "single" and
            bool(
                profile.ppimode or
                profile.bezels or
                profile.manual_offsets_useronly
            )
        )

        # Basic settings
        if (profile.spanmode == "single" and not legacy_advanced):
            self.radiobox_spanmode.SetSelection(0)
        elif (profile.spanmode == "advanced" or legacy_advanced):
            self.show_advanced_settings = True
            self.radiobox_spanmode.SetSelection(1)
        elif profile.spanmode == "multi":
            self.use_multi_image = True
            self.radiobox_spanmode.SetSelection(2)
        else:
            # default to simple span
            self.radiobox_spanmode.SetSelection(0)

        if profile.slideshow:
            self.cb_slideshow.SetValue(True)
            wx.PostEvent(self.cb_slideshow, wx.CommandEvent(commandEventType=wx.EVT_CHECKBOX.typeId))
            self.tc_sshow_delay.ChangeValue(str(profile.delay_list[0]/60))
            if profile.sortmode == "shuffle":
                self.ch_sshow_sort.SetSelection(0)
            elif profile.sortmode == "alphabetical":
                self.ch_sshow_sort.SetSelection(1)
            else:
                self.ch_sshow_sort.SetSelection(wx.NOT_FOUND)
        else:
            self.cb_slideshow.SetValue(False)
            wx.PostEvent(self.cb_slideshow, wx.CommandEvent(commandEventType=wx.EVT_CHECKBOX.typeId))
            self.tc_sshow_delay.Clear()
            self.ch_sshow_sort.SetSelection(wx.NOT_FOUND)

        if profile.hk_binding:
            self.cb_hotkey.SetValue(True)
            self.tc_hotkey_bind.ChangeValue(self.show_hkbinding(profile.hk_binding))
        else:
            self.cb_hotkey.SetValue(False)
            self.tc_hotkey_bind.Clear()
        wx.PostEvent(self.cb_hotkey, wx.CommandEvent(commandEventType=wx.EVT_CHECKBOX.typeId))


        # Advanced settings
        if self.show_advanced_settings:
            self.show_adv_setting_sizer(True)
            # profile.inches: not stored in profile anymore
            # profile.bezels: not stored in profile anymore
            if profile.manual_offsets_useronly:
                self.cb_offsets.SetValue(True)
                for tc, off in zip(self.tc_list_offsets, profile.manual_offsets_useronly):
                    offstr = "{},{}".format(off[0], off[1])
                    tc.SetValue(offstr)
            else:
                self.cb_offsets.SetValue(False)
            wx.PostEvent(self.cb_offsets, wx.CommandEvent(commandEventType=wx.EVT_CHECKBOX.typeId))
        else:
            self.show_adv_setting_sizer(False)

        # Paths displays: get number to show from profile.
        self.paths_array_to_listctrl(profile.paths_array)

        # Update wallpaper preview from selected profile
        if self.show_advanced_settings:
            display_data = self.display_sys.get_disp_list(True)
        else:
            display_data = self.display_sys.get_disp_list(False)
        self.wpprev_pnl.preview_wallpaper(
            profile.next_wallpaper_files(),
            self.show_advanced_settings,
            self.use_multi_image,
            display_data
        )
        self.wpprev_pnl.toggle_buttons(
            show_config = self.show_advanced_settings,
            in_config = False
        )



    def paths_array_to_listctrl(self, paths_array):
        self.refresh_path_listctrl(self.use_multi_image)
        if self.use_multi_image:
            for plist, idx in zip(paths_array, range(len(paths_array))):
                for pth in plist:
                    self.append_to_listctrl(
                        [str(idx), pth]
                    )
        else:
            for plist in paths_array:
                for pth in plist:
                    self.append_to_listctrl([pth])

    def show_hkbinding(self, hktuple):
        """Format a hotkey tuple into a '+' separated string."""
        if hktuple:
            hkstring = "+".join(hktuple)
            return hkstring
        else:
            return ""


    #
    # Helper methods
    #
    def update_choiceprofile(self):
        """Reload profile list into the choice box."""
        self.list_of_profiles = list_profiles()
        self.profnames = []
        for prof in self.list_of_profiles:
            self.profnames.append(prof.name)
        self.profnames.append("Create a new profile")
        self.choice_profiles.SetItems(self.profnames)

    def list_of_textctrl(self, ctrl_parent, num_disp):
        tcrtl_list = []
        for i in range(num_disp):
            tcrtl_list.append(
                wx.TextCtrl(ctrl_parent, -1,
                    size=(self.tc_width/2, -1),
                    style=wx.TE_RIGHT
                )
            )
        return tcrtl_list

    def sizer_toggle_children(self, sizer, bool_state, toggle_cb=False):
        for child in sizer.GetChildren():
            if child.IsSizer():
                self.sizer_toggle_children(child.GetSizer(), bool_state)
            else:
                widget = child.GetWindow()
                if (
                    isinstance(widget, wx.TextCtrl) or
                    isinstance(widget, wx.StaticText) or
                    isinstance(widget, wx.Choice) or
                    isinstance(widget, wx.Button) or
                    isinstance(widget, wx.CheckBox) and toggle_cb
                ):
                    widget.Enable(bool_state)

    def toggle_radio_and_profile_choice(self, enable):
        """Toggle enabled state of span mode radiobox and profile sizer children."""
        self.radiobox_spanmode.Enable(enable)
        self.sizer_toggle_children(self.sizer_profiles, enable)
        self.sizer_toggle_children(self.sizer_setting_diaginch, enable, True)
        if enable:
            try:
                diag_cb_state = self.cb_diaginch.GetValue()
                self.sizer_toggle_children(self.sizer_setting_diaginch, diag_cb_state)
            except AttributeError:
                pass

    def show_adv_setting_sizer(self, show_bool):
        """Show/Hide the sizer for advanced spanning settings."""
        self.sizer_setting_sizers.Show(self.sizer_setting_adv, show=show_bool)
        self.toggle_bezel_buttons(enable_config_butt=True)
        self.sizer_main.Layout()
        self.sizer_bottom_buttonrow.Show(self.button_align_test, show=show_bool)
        self.sizer_bottom_buttonrow.Layout()

    def toggle_bezel_buttons(self, bezel_mode = False, enable_config_butt = True):
        """Show/Hide bezel config buttons.

        If not in bezel mode show config button, and if in it hide config and show
        save and cancel buttons.
        enable_config_butt optional controls whether the config button should be
        enabled/disabled."""
        self.sizer_bezel_buttons.Show(self.button_bezels, show=not bezel_mode)
        self.sizer_bezel_buttons.Show(self.button_bezels_save, show=bezel_mode)
        self.sizer_bezel_buttons.Show(self.button_bezels_canc, show=bezel_mode)
        self.sizer_bezel_buttons.Layout()
        self.button_bezels.Enable(enable_config_butt)

    def refresh_path_listctrl(self, mult_img_bool):
        self.path_listctrl.Destroy()
        self.image_list.RemoveAll()
        if mult_img_bool:
            self.path_listctrl = wx.ListCtrl(self.statbox_parent_paths, -1,
                                              style=wx.LC_REPORT
                                              | wx.BORDER_SIMPLE
                                              | wx.LC_SORT_ASCENDING
                                             )
            self.path_listctrl.InsertColumn(0, 'Display', wx.LIST_FORMAT_RIGHT, width = 100)
            self.path_listctrl.InsertColumn(1, 'Source', width = 400)
        else:
            # show simpler listing without header if only one wallpaper target
            self.path_listctrl = wx.ListCtrl(self.statbox_parent_paths, -1,
                                              style=wx.LC_REPORT
                                              | wx.BORDER_SIMPLE
                                              | wx.LC_NO_HEADER
                                             )
            self.path_listctrl.InsertColumn(0, 'Source', width = 500)
        self.path_listctrl.SetImageList(self.image_list, wx.IMAGE_LIST_SMALL)
        self.sizer_setting_paths.Insert(1, self.path_listctrl, 1, wx.CENTER|wx.EXPAND|wx.ALL, 5)
        self.path_listctrl.InvalidateBestSize()
        self.sizer_main.Layout()

    def test_diag_value(self, inch_str):
        """Test that entered inch_str is a valid size and return it."""
        try:
            num = float(inch_str)
            if num > 0:
                return num
            else:
                return False
        except ValueError:
            return False


    #
    # Event methods
    #
    def onResize(self, event):
        self.resized = True
        self.wpprev_pnl.refresh_preview()

    def onIdle(self, event):
        leftdown = wx.GetMouseState().LeftIsDown()
        update = bool(self.resized and not leftdown)
        if update:
            self.wpprev_pnl.full_refresh_preview(update, self.show_advanced_settings, self.use_multi_image)
            self.resized = False
        else:
            event.Skip()


    def onSpanRadio(self, event):
        selection = self.radiobox_spanmode.GetSelection()
        if selection == 1:
            self.show_advanced_settings = True
            self.use_multi_image = False
        elif selection == 2:
            self.show_advanced_settings = False
            self.use_multi_image = True
        else:
            self.show_advanced_settings = False
            self.use_multi_image = False
        self.show_adv_setting_sizer(self.show_advanced_settings)
        self.refresh_path_listctrl(self.use_multi_image)
        display_data = self.display_sys.get_disp_list(self.show_advanced_settings)
        self.wpprev_pnl.update_display_data(
            display_data,
            self.show_advanced_settings,
            self.use_multi_image
        )
        self.wpprev_pnl.toggle_buttons(
            show_config = self.show_advanced_settings,
            in_config = False
        )


    def onCheckboxSlideshow(self, event):
        cb_state = self.cb_slideshow.GetValue()
        sizer = self.sizer_setting_slideshow
        self.sizer_toggle_children(sizer, cb_state)

    def onCheckboxHotkey(self, event):
        cb_state = self.cb_hotkey.GetValue()
        sizer = self.hotkey_bind_sizer
        self.sizer_toggle_children(sizer, cb_state)

    def onCheckboxBezels(self, event):
        cb_state = self.cb_bezels.GetValue()
        sizer = self.sizer_setting_bezels
        self.sizer_toggle_children(sizer, cb_state)

    def onCheckboxOffsets(self, event):
        cb_state = self.cb_offsets.GetValue()
        sizer = self.sizer_setting_offsets
        self.sizer_toggle_children(sizer, cb_state)

    def onCheckboxDiaginch(self, event):
        cb_state = self.cb_diaginch.GetValue()
        sizer = self.sizer_setting_diaginch
        self.sizer_toggle_children(sizer, cb_state)
        if cb_state == False:
            # revert to automatic detection and save
            self.display_sys.update_display_diags("auto")
            diags = [str(dsp.diagonal_size()[1]) for dsp in self.display_sys.disp_list]
            for tc, diag in zip(self.tc_list_diaginch, diags):
                tc.ChangeValue(diag)
            display_data = self.display_sys.get_disp_list(self.show_advanced_settings)
            self.wpprev_pnl.update_display_data(
                display_data,
                self.show_advanced_settings,
                self.use_multi_image
            )

    #
    # ListCtrl methods
    #

    def append_to_listctrl(self, data_row):
        if (self.use_multi_image and len(data_row) == 2):
            img_id = self.add_to_imagelist(data_row[1])
            index = self.path_listctrl.InsertItem(self.path_listctrl.GetItemCount(), data_row[0], img_id)
            self.path_listctrl.SetItem(index, 1, data_row[1])
        elif (not self.use_multi_image and len(data_row) == 1):
            img_id = self.add_to_imagelist(data_row[0])
            index = self.path_listctrl.InsertItem(self.path_listctrl.GetItemCount(), data_row[0], img_id)
        else:
            sp_logging.G_LOGGER.info("UseMultImg: %s. Bad data_row: %s",
                                     self.use_multi_image, data_row)

    def add_to_imagelist(self, path):
        folder_bmp =  wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_TOOLBAR, self.tsize)
        if os.path.isdir(path):
            img_id = self.image_list.Add(folder_bmp)
        else:
            thumb_bmp = self.create_thumb_bmp(path)
            img_id = self.image_list.Add(thumb_bmp)
        return img_id

    def create_thumb_bmp(self, filename):
        wximg = wx.Image(filename, type=wx.BITMAP_TYPE_ANY)
        imgsize = wximg.GetSize()
        w2h_ratio = imgsize[0]/imgsize[1]
        if w2h_ratio > 1:
            target_w = self.tsize[0]
            target_h = target_w/w2h_ratio
            pos = (0, round((target_w - target_h)/2))
        else:
            target_h = self.tsize[1]
            target_w = target_h*w2h_ratio
            pos = (round((target_h - target_w)/2), 0)
        bmp = wximg.Scale(target_w, target_h).Resize(self.tsize, pos).ConvertToBitmap()
        return bmp

    def populate_lc_browse(self, pathslist, imglist):
        for path_item in pathslist:
            self.append_to_listctrl(path_item)

    #
    # Top level button definitions
    #
    def onOverrideSizes(self, event):
        self.create_sizer_diaginch_override()

    def onSaveDiagInch(self, event):
        """Save user modified display sizes to DisplaySystem."""
        inches = []
        for tc in self.tc_list_diaginch:
            tc_val = tc.GetValue()
            user_inch = self.test_diag_value(tc_val)
            if user_inch:
                inches.append(user_inch)
            else:
                # error msg
                msg = ("Display size must be a positive number, "
                       "'{}' was entered.".format(tc_val))
                sp_logging.G_LOGGER.info(msg)
                dial = wx.MessageDialog(self, msg, "Error", wx.OK|wx.STAY_ON_TOP|wx.CENTRE)
                dial.ShowModal()
                return -1
        self.display_sys.update_display_diags(inches)
        display_data = self.display_sys.get_disp_list(self.show_advanced_settings)
        self.wpprev_pnl.update_display_data(
            display_data,
            self.show_advanced_settings,
            self.use_multi_image
        )

    def onConfigureBezels(self, event):
        """Start bezel size config mode."""
        self.toggle_radio_and_profile_choice(False)
        self.wpprev_pnl.start_bezel_config()
        self.button_bezels.Hide()
        self.button_bezels_save.Show()
        self.button_bezels_canc.Show()

    def onConfigureBezelsSave(self, event):
        """Save out of bezel size config mode."""
        self.toggle_radio_and_profile_choice(True)
        self.wpprev_pnl.bezel_config_save()
        self.button_bezels_save.Hide()
        self.button_bezels_canc.Hide()
        self.button_bezels.Show()

    def onConfigureBezelsCanc(self, event):
        """Cancel out of bezel size config mode."""
        self.toggle_radio_and_profile_choice(True)
        self.wpprev_pnl.bezel_config_cancel()
        self.button_bezels_save.Hide()
        self.button_bezels_canc.Hide()
        self.button_bezels.Show()

    def onBrowsePaths(self, event):
        """Opens the pick paths dialog."""
        dlg = BrowsePaths(self, self.use_multi_image, self.defdir)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            path_list_data = dlg.path_list_data
            image_list = dlg.il
            self.defdir = dlg.defdir
            self.populate_lc_browse(path_list_data, image_list)
        dlg.Destroy()

    def onRemoveSource(self, event):
        """Removes selection from wallpaper source ListCtrl."""
        item = self.path_listctrl.GetFocusedItem()
        if item != -1:
            self.path_listctrl.DeleteItem(item)

    def onClose(self, event):
        """Closes the profile config panel."""
        self.frame.Close(True)

    def onSelect(self, event):
        """Acts once a profile is picked in the dropdown menu."""
        event_object = event.GetEventObject()
        if event_object.GetName() == "ProfileChoice":
            item = event.GetSelection()
            if event.GetString() == "Create a new profile":
                self.onCreateNewProfile(event)
            else:
                self.populate_fields(self.list_of_profiles[item])
        else:
            pass

    def onApply(self, event):
        """Applies the currently open profile. Saves it first."""
        saved_file = self.onSave(event)
        sp_logging.G_LOGGER.info("onApply profile: saved %s", saved_file)
        if saved_file:
            saved_profile = ProfileData(saved_file)
            self.parent_tray_obj.reload_profiles(event)
            self.parent_tray_obj.start_profile(event, saved_profile)
        else:
            pass

    def onSave(self, event):
        """Saves currently open profile into file. A test method is called to verify data."""
        tmp_profile = TempProfileData()
        tmp_profile.name = self.tc_name.GetLineText(0)
        tmp_profile.slideshow = self.cb_slideshow.GetValue()
        if tmp_profile.slideshow:
            tmp_profile.delay = str(60*float(self.tc_sshow_delay.GetLineText(0))) # save delay as seconds for compatibility!
            tmp_profile.sortmode = self.ch_sshow_sort.GetString(self.ch_sshow_sort.GetSelection()).lower()
        if self.cb_hotkey.GetValue():
            tmp_profile.hk_binding = self.tc_hotkey_bind.GetLineText(0)

        # span mode
        span_sel = self.radiobox_spanmode.GetSelection()
        if span_sel == 0:
            tmp_profile.spanmode = "single"
        elif span_sel == 1:
            tmp_profile.spanmode = "advanced"
        elif span_sel == 2:
            tmp_profile.spanmode = "multi"

        # manual offsets
        if self.cb_offsets.GetValue():
            offs_strs = []
            for tc in self.tc_list_offsets:
                line = tc.GetLineText(0)
                if line:
                    offs_strs.append(line)
                else:
                    # if offset field is empty, assume user wants no offset
                    offs_strs.append("0,0")
            tmp_profile.manual_offsets = ";".join(offs_strs)

        # Paths
        # for text_field in self.paths_controls: # TODO
        # extract data from path_listctrl
        path_lc_contents = []
        columns = self.path_listctrl.GetColumnCount()
        for idx in range(self.path_listctrl.GetItemCount()):
            item_dat = []
            for col in range(columns):
                item_dat.append(self.path_listctrl.GetItemText(idx, col))
            path_lc_contents.append(item_dat)

        # format data
        paths_array = []
        if columns == 1:
            flat_contents = [path for row in path_lc_contents for path in row]
            semicol_sep_paths = ";".join(flat_contents)
            tmp_profile.paths_array.append(semicol_sep_paths)
        else:
            path_lc_contents = sorted(path_lc_contents, key=itemgetter(0))
            paths_dict = {}
            for row in path_lc_contents:
                disp_id, path_item = row
                if disp_id in paths_dict:
                    paths_dict[disp_id].append(path_item)
                else:
                    paths_dict[disp_id] = [path_item]
            # print(paths_dict)
            for disp_id in paths_dict:
                semicol_sep_paths = ";".join(paths_dict[disp_id])
                tmp_profile.paths_array.append(semicol_sep_paths)

        # log
        sp_logging.G_LOGGER.info(tmp_profile.name)
        sp_logging.G_LOGGER.info(tmp_profile.spanmode)
        sp_logging.G_LOGGER.info(tmp_profile.slideshow)
        sp_logging.G_LOGGER.info(tmp_profile.delay)
        sp_logging.G_LOGGER.info(tmp_profile.sortmode)
        sp_logging.G_LOGGER.info(tmp_profile.manual_offsets)
        sp_logging.G_LOGGER.info(tmp_profile.hk_binding)
        sp_logging.G_LOGGER.info(tmp_profile.paths_array)

        # test collected data and save if it is valid, otherwise pass
        if tmp_profile.test_save():
            saved_file = tmp_profile.save()
            self.update_choiceprofile()
            self.parent_tray_obj.reload_profiles(event)
            self.parent_tray_obj.register_hotkeys()
            self.choice_profiles.SetSelection(self.choice_profiles.FindString(tmp_profile.name))
            # Update wallpaper preview from selected profile
            saved_profile = ProfileData(saved_file)
            if self.show_advanced_settings:
                display_data = self.display_sys.get_disp_list(True)
            else:
                display_data = self.display_sys.get_disp_list(False)
            self.wpprev_pnl.preview_wallpaper(
                saved_profile.next_wallpaper_files(),
                self.show_advanced_settings,
                self.use_multi_image,
                display_data
            )
            return saved_file
        else:
            sp_logging.G_LOGGER.info("test_save failed.")
            return None


    def onCreateNewProfile(self, event):
        """Empties the wallpaper profile config fields."""
        self.choice_profiles.SetSelection(
            self.choice_profiles.FindString("Create a new profile")
            )

        self.tc_name.ChangeValue("")

        self.radiobox_spanmode.SetSelection(0)
        self.onSpanRadio(None)

        self.cb_slideshow.SetValue(False)
        self.tc_sshow_delay.ChangeValue("")
        self.ch_sshow_sort.SetSelection(wx.NOT_FOUND)
        self.onCheckboxSlideshow(None)

        self.cb_offsets.SetValue(False)
        for tc in self.tc_list_offsets:
            tc.SetValue("0,0")
        self.onCheckboxOffsets(None)

        self.cb_hotkey.SetValue(False)
        self.tc_hotkey_bind.ChangeValue("")
        self.onCheckboxHotkey(None)

        self.refresh_path_listctrl(False)

        # refresh wallpaper preview back to black previews
        self.wpprev_pnl.draw_displays()


    def onDeleteProfile(self, event):
        """Deletes the currently selected profile after getting confirmation."""
        profname = self.tc_name.GetLineText(0)
        fname = os.path.join(PROFILES_PATH, profname + ".profile")
        file_exists = os.path.isfile(fname)
        if not file_exists:
            msg = "Selected profile is not saved."
            show_message_dialog(msg, "Error")
            return
        # Open confirmation dialog
        dlg = wx.MessageDialog(None,
                               "Do you want to delete profile: {}?".format(profname),
                               'Confirm Delete',
                               wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        if result == wx.ID_YES and file_exists:
            os.remove(fname)
            self.update_choiceprofile()
            self.onCreateNewProfile(None)
        else:
            pass

    def onAlignTest(self, event):
        """Align test, takes alignment settings from open profile and sets a test image wp."""
        # Use the settings currently written out in the fields!
        testimage = [os.path.join(PATH, "superpaper/resources/test.png")]
        if not os.path.isfile(testimage[0]):
            msg = "Test image not found in {}.".format(testimage)
            show_message_dialog(msg, "Error")
        ppi = None
        inches = self.tc_inches.GetLineText(0).split(";")
        if (inches == "") or (len(inches) < wpproc.NUM_DISPLAYS):
            msg = "You must enter a diagonal inch value for every \
display, serparated by a semicolon ';'."
            show_message_dialog(msg, "Error")

        inches = [float(i) for i in inches]
        bezels = self.tc_bez.GetLineText(0).split(";")
        bezels = [float(b) for b in bezels]
        offsets = self.tc_offsets.GetLineText(0).split(";")
        offsets = [[int(i.split(",")[0]), int(i.split(",")[1])] for i in offsets]
        flat_offsets = []
        for off in offsets:
            for pix in off:
                flat_offsets.append(pix)

        # Use the simplified CLI profile class
        get_display_data()
        profile = CLIProfileData(testimage,
                                 ppi,
                                 inches,
                                 bezels,
                                 flat_offsets,
                                )
        change_wallpaper_job(profile)

    def onHelp(self, event):
        """Open help dialog."""
        help_frame = HelpFrame()






class WallpaperPreviewPanel(wx.Panel):
    """
    Wallpaper & monitor preview panel.

    Previews wallpaper settings as applied to the input image.
    In the advanced mode allows the user to enter their monitor
    setup, which will then be saved into a file as a monitor
    configuration. Method looks up saved setups to see if one
    exists that matches the given resolutions, offsets and sizes.
    """
    def __init__(self, parent, display_sys, image_list = None, use_ppi_px = False, use_multi_image = False):
        self.preview_size = (1200,450)
        wx.Panel.__init__(self, parent, size=self.preview_size)
        self.frame = parent

        # Buttons
        self.config_mode = False
        self.bezel_conifg_mode = False
        self.create_buttons(use_ppi_px)

        # Colour definitions
        self.clr_prw_mntr = wx.Colour(0, 0, 0, alpha=wx.ALPHA_OPAQUE)
        self.clr_prw_bkg = wx.Colour(30, 30, 30, alpha=wx.ALPHA_OPAQUE)
        self.SetBackgroundColour(self.clr_prw_bkg)
        
        # Display data and sizes
        self.display_sys = display_sys
        self.display_data = self.display_sys.get_disp_list()
        self.dtop_canvas_px = self.get_canvas(self.display_data)
        self.dtop_canvas_relsz, self.dtop_canvas_pos, scaling_fac = self.fit_canvas_wrkarea(self.dtop_canvas_px)
        self.display_rel_sizes = self.displays_on_canvas(self.display_data, self.dtop_canvas_pos, scaling_fac)

        # bitmaps to be shown
        self.current_preview_images = []
        self.preview_img_list = []
        self.bmp_list = []

        # Draw preview
        self.draw_displays()

        # Create bezel buttons for displays in preview
        self.bez_buttons = []
        self.create_bezel_buttons()


    #
    # UI drawing methods
    #
    def draw_displays(self, use_ppi_px = False, use_multi_image = False):
        work_sz = self.GetSize()

        # draw canvas
        bmp_canv = wx.Bitmap.FromRGBA(self.dtop_canvas_relsz[0], self.dtop_canvas_relsz[1], red=0, green=0, blue=0, alpha=255)
        if not self.preview_img_list:
            # preview StaticBitmaps don't exist yet
            self.bmp_list.append(bmp_canv)
            self.st_bmp_canvas = wx.StaticBitmap(self, wx.ID_ANY, bmp_canv)
            self.st_bmp_canvas.SetPosition(self.dtop_canvas_pos)
            self.st_bmp_canvas.Hide()

            # draw monitor previews
            for disp in self.display_rel_sizes:
                size = disp[0]
                offs = disp[1]
                bmp = wx.Bitmap.FromRGBA(size[0], size[1], red=0, green=0, blue=0, alpha=255)
                self.bmp_list.append(bmp)
                st_bmp = wx.StaticBitmap(self, wx.ID_ANY, bmp)
                # st_bmp.SetScaleMode(wx.Scale_AspectFill)  # New in wxpython 4.1
                st_bmp.SetPosition(offs)
                self.preview_img_list.append(st_bmp)
        else:
            # previews exist and should be blanked
            self.current_preview_images = [] # drop chached image list

            self.st_bmp_canvas.SetBitmap(bmp_canv)
            self.st_bmp_canvas.SetPosition(self.dtop_canvas_pos)
            self.st_bmp_canvas.Hide()

            # blank monitor previews
            for disp, st_bmp in zip(self.display_rel_sizes, self.preview_img_list):
                size = disp[0]
                offs = disp[1]
                bmp = wx.Bitmap.FromRGBA(size[0], size[1], red=0, green=0, blue=0, alpha=255)
                st_bmp.SetBitmap(bmp)
                st_bmp.SetPosition(offs)

        self.draw_monitor_numbers(use_ppi_px)

    def resize_displays(self, use_ppi_px):
        if use_ppi_px:
            for (disp,
                 img_sz,
                 bez_szs,
                 st_bmp) in zip(self.display_rel_sizes,
                                self.img_rel_sizes,
                                self.bz_rel_sizes,
                                self.preview_img_list):
                size, offs = disp
                bmp = wx.Bitmap.FromRGBA(img_sz[0], img_sz[1], red=0, green=0, blue=0, alpha=255)
                bmp_w_bez = self.bezels_to_bitmap(bmp, size, bez_szs)
                st_bmp.SetSize(size)
                st_bmp.SetPosition(offs)
                st_bmp.SetBitmap(bmp_w_bez)
        else:
            for disp, st_bmp in zip(self.display_rel_sizes, self.preview_img_list):
                size = disp[0]
                offs = disp[1]
                bmp = wx.Bitmap.FromRGBA(size[0], size[1], red=0, green=0, blue=0, alpha=255)
                st_bmp.SetBitmap(bmp)
                st_bmp.SetPosition(offs)
                st_bmp.SetSize(size)
        self.draw_monitor_numbers(use_ppi_px)

    def draw_monitor_numbers(self, use_ppi_px):
        font = wx.Font(24, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        font_clr = wx.Colour(60, 60, 60, alpha=wx.ALPHA_OPAQUE)

        for st_bmp in self.preview_img_list:
            bmp = st_bmp.GetBitmap()
            dc = wx.MemoryDC(bmp)
            text = str(self.preview_img_list.index(st_bmp))
            dc.SetTextForeground(font_clr)
            dc.SetFont(font)
            dc.DrawText(text, 5, 5)
            del dc
            st_bmp.SetBitmap(bmp)

        if use_ppi_px:
            self.draw_monitor_sizes()

    def draw_monitor_sizes(self):
        font = wx.Font(24, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_LIGHT)
        font_clr = wx.Colour(60, 60, 60, alpha=wx.ALPHA_OPAQUE)

        for st_bmp, img_sz, dsp in zip(self.preview_img_list,
                                       self.img_rel_sizes,
                                       self.display_sys.disp_list):
            bmp = st_bmp.GetBitmap()
            dc = wx.MemoryDC(bmp)
            text = str(dsp.diagonal_size()[1]) + '"'
            dc.SetTextForeground(font_clr)
            dc.SetFont(font)
            # bmp_w, bmp_h = dc.GetSize()
            bmp_w, bmp_h = img_sz
            text_w, text_h = dc.GetTextExtent(text)
            pos_w = bmp_w - text_w - 5
            pos_h = 5
            dc.DrawText(text, pos_w, pos_h)
            del dc
            st_bmp.SetBitmap(bmp)


    def refresh_preview(self, use_ppi_px = False):
        if not self.config_mode:
            self.dtop_canvas_px = self.get_canvas(self.display_data, use_ppi_px)
            self.dtop_canvas_relsz, self.dtop_canvas_pos, scaling_fac = self.fit_canvas_wrkarea(self.dtop_canvas_px)
            self.st_bmp_canvas.SetPosition(self.dtop_canvas_pos)
            self.st_bmp_canvas.SetSize(self.dtop_canvas_relsz)

            if use_ppi_px:
                (self.display_rel_sizes,
                    self.img_rel_sizes,
                    self.bz_rel_sizes) = self.displays_on_canvas(
                        self.display_data, self.dtop_canvas_pos,
                        scaling_fac, use_ppi_px
                    )
            else:
                self.display_rel_sizes = self.displays_on_canvas(
                    self.display_data, self.dtop_canvas_pos, scaling_fac
                )
            for disp, st_bmp in zip(self.display_rel_sizes, self.preview_img_list):
                size = disp[0]
                offs = disp[1]
                st_bmp.SetPosition(offs)
                st_bmp.SetSize(size)

        self.move_buttons()
        self.move_bezel_buttons()

    def full_refresh_preview(self, is_resized, use_ppi_px, use_multi_image):
        if is_resized and not self.config_mode:
            dtop_canvas_relsz, dtop_canvas_pos, scaling_fac = self.fit_canvas_wrkarea(self.dtop_canvas_px)
            # if (self.current_preview_images and dtop_canvas_relsz is not self.dtop_canvas_relsz):
            if (self.current_preview_images):
                self.preview_wallpaper(self.current_preview_images, use_ppi_px, use_multi_image)
                self.move_bezel_buttons()
            else:
                self.refresh_preview(use_ppi_px)
                self.resize_displays(use_ppi_px)
                self.move_bezel_buttons()

    def preview_wallpaper(self, image_list, use_ppi_px = False, use_multi_image = False, display_data = None):
        if display_data:
            self.display_data = display_data
        self.refresh_preview(use_ppi_px)
        self.current_preview_images = image_list

        if use_multi_image:
            # hide canvas and set images to monitor previews
            self.st_bmp_canvas.Hide()
            for img_nm, dprev in zip(image_list, self.preview_img_list):
                prev_sz = dprev.GetSize()
                dprev.SetBitmap(self.resize_and_bitmap(img_nm, prev_sz))
                dprev.Show()
        elif use_ppi_px:
            img = image_list[0]
            # set canvas to fit with keeping aspect the image, with dim/blur
            # and crop pieces to show on monitor previews unaltered.
            # With use_ppi_px any provided bezels will be drawn.
            canv_sz = self.st_bmp_canvas.GetSize()
            bmp_clr, bmp_bw = self.resize_and_bitmap(img, canv_sz, True)
            self.st_bmp_canvas.SetBitmap(bmp_bw)
            self.st_bmp_canvas.Show()

            canvas_pos = self.dtop_canvas_pos
            for (disp,
                 img_sz,
                 bez_szs,
                 st_bmp) in zip(self.display_rel_sizes,
                                self.img_rel_sizes,
                                self.bz_rel_sizes,
                                self.preview_img_list):
                sz = disp[0]
                pos = (disp[1][0] - canvas_pos[0], disp[1][1] - canvas_pos[1])
                crop = bmp_clr.GetSubBitmap(wx.Rect(pos, img_sz))
                crop_w_bez = self.bezels_to_bitmap(crop, sz, bez_szs)
                st_bmp.SetBitmap(crop_w_bez)
                st_bmp.Show()
        else:
            img = image_list[0]
            # set canvas to fit with keeping aspect the image, with dim/blur
            # and crop pieces to show on monitor previews unaltered.
            canv_sz = self.st_bmp_canvas.GetSize()
            bmp_clr, bmp_bw = self.resize_and_bitmap(img, canv_sz, True)
            self.st_bmp_canvas.SetBitmap(bmp_bw)
            self.st_bmp_canvas.Show()

            canvas_pos = self.dtop_canvas_pos
            for disp, st_bmp in zip(self.display_rel_sizes, self.preview_img_list):
                sz = disp[0]
                pos = (disp[1][0] - canvas_pos[0], disp[1][1] - canvas_pos[1])
                crop = bmp_clr.GetSubBitmap(wx.Rect(pos, sz))
                st_bmp.SetBitmap(crop)
                st_bmp.Show()
        self.draw_monitor_numbers(use_ppi_px)

    def resize_and_bitmap(self, fname, size, enhance_color = False):
        """Take filename of an image and resize and center crop it to size."""
        pil = resize_to_fill(Image.open(fname), size)
        img = wx.Image(pil.size[0], pil.size[1])
        img.SetData(pil.convert("RGB").tobytes())
        if enhance_color:
            converter = ImageEnhance.Color(pil)
            pilenh_bw = converter.enhance(0.25)
            brightns = ImageEnhance.Brightness(pilenh_bw)
            pilenh = brightns.enhance(0.45)
            imgenh = wx.Image(pil.size[0], pil.size[1])
            imgenh.SetData(pilenh.convert("RGB").tobytes())
            return (img.ConvertToBitmap(), imgenh.ConvertToBitmap())
        return img.ConvertToBitmap()

    def bezels_to_bitmap(self, bmp, disp_sz, bez_rects):
        """Add bezel rectangles ( right_bez , bottom_bez ) to given bitmap."""
        sp_logging.G_LOGGER.info("bezels_to_bitmap: bez_rects: %s", bez_rects)
        right_bez, bottom_bez = bez_rects
        if (right_bez == (0, 0) and bottom_bez == (0, 0)):
            return bmp
        # bmp into wx.Image and new output
        img = bmp.ConvertToImage()
        img_sz = img.GetSize()
        img_out = wx.Image(disp_sz[0], disp_sz[1])
        img_out.Paste(img, 0, 0)

        # Add bezels sequentially to the Image
        # bottom bez
        if bottom_bez != (0, 0):
            b_bez_bmp = wx.Bitmap.FromRGBA(bottom_bez[0], bottom_bez[1],
                                           red=5, green=5, blue=5, alpha=100)
            b_bez_img = b_bez_bmp.ConvertToImage()
            img_out.Paste(b_bez_img, 0, img_sz[1])

        # right bez: is longer if bottom bez is present
        if right_bez != (0, 0):
            r_bez_bmp = wx.Bitmap.FromRGBA(right_bez[0], right_bez[1],
                                           red=5, green=5, blue=5, alpha=100)
            r_bez_img = r_bez_bmp.ConvertToImage()
            img_out.Paste(r_bez_img, img_sz[0], 0)

        # Convert Image back to wx.Bitmap
        return img_out.ConvertToBitmap()


    def update_display_data(self, display_data, use_ppi_px, use_multi_image):
        self.display_data = display_data
        self.refresh_preview()
        self.full_refresh_preview(True, use_ppi_px, use_multi_image)


    #
    # Data analysis methods
    #
    def get_canvas(self, disp_data, use_ppi_px = False):
        """Returns a size tuple for the desktop are in pixels or millimeters."""
        if use_ppi_px: # TODO This is unnecessary if digital offsets contain the bezels
            rightmost_edge = max(
                [disp.resolution[0] + disp.digital_offset[0] + disp.ppi_norm_bezels[0] for disp in disp_data]
            )
            bottommost_edge = max(
                [disp.resolution[1] + disp.digital_offset[1] + disp.ppi_norm_bezels[1] for disp in disp_data]
            )
        else:
            rightmost_edge = max(
                [disp.resolution[0] + disp.digital_offset[0] for disp in disp_data]
            )
            bottommost_edge = max(
                [disp.resolution[1] + disp.digital_offset[1] for disp in disp_data]
            )
        return (rightmost_edge, bottommost_edge)

    def fit_canvas_wrkarea(self, canvas_px):
        """Compute canvas size relative to the background panel size.

        Returns a size tuple in so that along the longer
        edge of the canvas, at most 90% of the panel dimensions are used.
        
        Input is either canvas size in true pixels or in PPI normalized
        pixels."""
        rel_factor = 0.9
        rel_achor_gap = (1-rel_factor)/2
        work_sz = self.GetSize()
        w2h_ratio_worksz = work_sz[0]/work_sz[1]
        w2h_ratio = canvas_px[0]/canvas_px[1]
        if w2h_ratio > w2h_ratio_worksz:
            # canvas is wider than working area
            # limit width to 90% of working area
            new_width = rel_factor * work_sz[0]
            scaling_fac = new_width/canvas_px[0]
            new_height = scaling_fac * canvas_px[1]
            anchor_left = rel_achor_gap * work_sz[0]
            anchor_top = (work_sz[1] - new_height) / 2
        else:
            # canvas is taller than working area
            new_height = rel_factor * work_sz[1]
            scaling_fac = new_height/canvas_px[1]
            new_width = scaling_fac * canvas_px[0]
            anchor_left = (work_sz[0] - new_width)/2
            anchor_top = rel_achor_gap * work_sz[1]
        canvas_rel = (new_width, new_height)
        canvas_rel_pos = (anchor_left, anchor_top)
        return (canvas_rel, canvas_rel_pos, scaling_fac)

    def displays_on_canvas(self, disp_data, canvas_pos, scaling_fac, use_ppi_px=False):
        """Return sizes and positions of displays in disp_data on the working area.

        if use_ppi_px == True, returned display sizes contain bezels and lists of
        image sizes and bezel rectangles are returned separately.
        bz_szs is a list of size tuples pairs, each in pair for each possible bezel.
        """
        if use_ppi_px:
            display_szs_pos = []
            image_szs = []
            bz_szs = []
            for disp in disp_data:
                res = disp.resolution
                doff = disp.digital_offset
                off = canvas_pos
                bez = disp.ppi_norm_bezels
                display_szs_pos.append(
                    (
                        # tuple 1: size = res + bez
                        (
                            scaling_fac * (res[0] + bez[0]),
                            scaling_fac * (res[1] + bez[1])
                        ),
                        # tuple 2: pos
                        (
                            (scaling_fac * doff[0]) + off[0], # TODO do you add bezel here?
                            (scaling_fac * doff[1]) + off[1]
                        )
                    )
                )
                image_szs.append(
                    (
                        scaling_fac * res[0],
                        scaling_fac * res[1]
                    )
                )
                if bez[0] != 0:
                    right_bez = (scaling_fac * bez[0],
                                 scaling_fac * (res[1] + bez[1]))
                else:
                    right_bez = (0, 0)
                if bez[1] != 0:
                    bottom_bez = (scaling_fac * res[0], scaling_fac * bez[1])
                else:
                    bottom_bez = (0, 0)
                bz_szs.append(
                    (right_bez, bottom_bez)
                )
            return [display_szs_pos, image_szs, bz_szs]
        else:
            display_szs_pos = []
            for disp in disp_data:
                doff = disp.digital_offset
                off = canvas_pos
                display_szs_pos.append(
                    (
                        tuple([px*scaling_fac for px in disp.resolution]),
                        tuple([doff[0]*scaling_fac + off[0], doff[1]*scaling_fac + off[1]])
                    )
                )
            return display_szs_pos



    #
    # Buttons
    #
    def create_buttons(self, use_ppi_px):
        """Create buttons for display preview positioning config."""
        # Buttons - show only if use_ppi_px == True
        self.button_config = wx.Button(self, label="Positions")
        self.button_save = wx.Button(self, label="Save")
        self.button_reset = wx.Button(self, label="Reset")
        self.button_cancel = wx.Button(self, label="Cancel")

        self.button_config.Bind(wx.EVT_BUTTON, self.onConfigure)
        self.button_save.Bind(wx.EVT_BUTTON, self.onSave)
        self.button_reset.Bind(wx.EVT_BUTTON, self.onReset)
        self.button_cancel.Bind(wx.EVT_BUTTON, self.onCancel)

        self.move_buttons()

        self.button_config.Show(use_ppi_px)
        self.button_save.Show(False)
        self.button_reset.Show(False)
        self.button_cancel.Show(False)

    def move_buttons(self):
        """Position display config buttons to bottom right corner."""
        sz_area = self.GetSize()
        sz_butt = self.button_config.GetDefaultSize()
        self.butt_gap = 10
        self.button_config.SetPosition(
            (
                sz_area[0] - sz_butt[0] - self.butt_gap,
                sz_area[1] - sz_butt[1] - self.butt_gap
            )
        )
        self.button_save.SetPosition(
            (
                sz_area[0] - 2*(sz_butt[0] + self.butt_gap),
                sz_area[1] - sz_butt[1] - self.butt_gap
            )
        )
        self.button_reset.SetPosition(
            (
                sz_area[0] - sz_butt[0] - self.butt_gap,
                sz_area[1] - 2*(sz_butt[1] + self.butt_gap)
            )
        )
        self.button_cancel.SetPosition(
            (
                sz_area[0] - sz_butt[0] - self.butt_gap,
                sz_area[1] - sz_butt[1] - self.butt_gap
            )
        )

    def toggle_buttons(self, show_config, in_config):
        """Toggle visibility of display positioning config buttons."""
        self.button_config.Show(show_config)
        self.button_save.Show(in_config)
        self.button_reset.Show(in_config)
        self.button_cancel.Show(in_config)

    def onConfigure(self, evt):
        """Start diplay position config mode."""
        self.frame.toggle_radio_and_profile_choice(False)
        self.config_mode = True
        self.toggle_buttons(False, True)
        self.show_staticbmps(False)
        self.create_shapes()

    def onSave(self, evt):
        """Save current Display offsets into DisplaySystem."""
        self.config_mode = False
        self.toggle_buttons(True, False)
        # Export and save offsets to DisplaySystem
        self.export_offsets(self.display_sys)
        self.display_sys.save_system()
        display_data = self.display_sys.get_disp_list(use_ppi_norm = True)
        # Full redraw of preview with new offset data
        if self.current_preview_images:
            self.preview_wallpaper(self.current_preview_images, True, False, display_data=display_data)
        else:
            self.display_data = display_data
            self.refresh_preview(True)
            self.resize_displays(True)
            self.show_staticbmps(True)
        self.draggable_shapes = []  # Destroys DragShapes
        self.frame.toggle_radio_and_profile_choice(True)

    def onReset(self, evt):
        """Reset Display preview positions to the initial guess."""
        # Back up current offsets
        ppinorm_offs = self.display_sys.get_ppinorm_offsets()
        # Compute and get reset offsets
        self.display_sys.compute_initial_preview_offsets()
        display_data = self.display_sys.get_disp_list(use_ppi_norm = True)
        dtop_canvas_px = self.get_canvas(display_data, True)
        dtop_canvas_relsz, dtop_canvas_pos, scaling_fac = self.fit_canvas_wrkarea(dtop_canvas_px)
        (display_rel_sizes,
            img_rel_sizes,
            bz_rel_sizes) = self.displays_on_canvas(
                display_data, dtop_canvas_pos,
                scaling_fac, True
            )
        # Move display preview draggable_shapes
        for shp, off in zip(self.draggable_shapes, display_rel_sizes):
            shp.pos = off[1]
        # Restore backed up offsets
        self.display_sys.update_ppinorm_offsets(ppinorm_offs)
        self.Refresh()

    def onCancel(self, evt):
        """Cancel out of diplay position config mode."""
        self.config_mode = False
        self.toggle_buttons(True, False)
        self.draggable_shapes = []  # Destroys DragShapes
        self.refresh_preview()
        self.full_refresh_preview(True, True, False)
        self.show_staticbmps(True)
        self.frame.toggle_radio_and_profile_choice(True)


    def show_staticbmps(self, show):
        """Show/Hide StaticBitmaps."""
        if self.current_preview_images:
            self.st_bmp_canvas.Show(show)
        else:
            self.st_bmp_canvas.Show(False)
        for st_bmp in self.preview_img_list:
            st_bmp.Show(show)

    def export_offsets(self, display_sys):
        """Read dragged preview positions, normalize them to be positive,
        and scale sizes up to old canvas size."""
        # DragShape sizes and positions need to be scaled up by true_canvas_old_w/preview_canv_w
        prev_canv_w = self.st_bmp_canvas.GetSize()[0]
        true_canv_w = self.get_canvas(display_sys.get_disp_list(True))[0]
        scaling = true_canv_w / prev_canv_w
        sanitzed_offs = self.sanitize_shape_offs()
        ppi_norm_offsets = []
        for off in sanitzed_offs:
            ppi_norm_offsets.append(
                (
                    off[0]*scaling,
                    off[1]*scaling
                )
            )
        display_sys.update_ppinorm_offsets(ppi_norm_offsets, bezels_included = False)

    def sanitize_shape_offs(self):
        """Return shapes' relative offsets, anchoring to (0,0)."""
        sanitized_offs = []
        leftmost_offset = min([shape.pos[0] for shape in self.draggable_shapes])
        topmost_offset = min([shape.pos[1] for shape in self.draggable_shapes])
        for shape in self.draggable_shapes:
            sanitized_offs.append(
                (
                    shape.pos[0] - leftmost_offset,
                    shape.pos[1] - topmost_offset
                )
            )
        return sanitized_offs

    #
    # DragImage methods
    #

    class DragShape:
        def __init__(self, bmp):
            self.bmp = bmp
            self.pos = (0,0)
            self.shown = True
            self.text = None
            self.fullscreen = False

        def HitTest(self, pt):
            rect = self.GetRect()
            return rect.Contains(pt)

        def GetRect(self):
            return wx.Rect(self.pos[0], self.pos[1],
                        self.bmp.GetWidth(), self.bmp.GetHeight())

        def Draw(self, dc, op = wx.COPY):
            if self.bmp.IsOk():
                memDC = wx.MemoryDC()
                memDC.SelectObject(self.bmp)

                dc.Blit(self.pos[0], self.pos[1],
                        self.bmp.GetWidth(), self.bmp.GetHeight(),
                        memDC, 0, 0, op, True)

                return True
            else:
                return False



    def create_shapes(self):
        """Create draggable objects from display previews."""
        self.draggable_shapes = []
        self.drag_image = None
        self.drag_shape = None

        for st_bmp in self.preview_img_list:
            shape = self.DragShape(st_bmp.GetBitmap())
            shape.pos = st_bmp.GetPosition()
            self.draggable_shapes.append(shape)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)


    def draw_shapes(self, dc):
        for shape in self.draggable_shapes:
            if shape.shown:
                shape.Draw(dc)

    def find_shape(self, pt):
        for shape in self.draggable_shapes:
            if shape.HitTest(pt):
                return shape
        return None

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        self.draw_shapes(dc)

    def OnLeftDown(self, evt):
        # Did the mouse go down on one of our shapes?
        shape = self.find_shape(evt.GetPosition())

        # If a shape was 'hit', then set that as the shape we're going to
        # drag around. Get our start position. Dragging has not yet started.
        # That will happen once the mouse moves, OR the mouse is released.
        if shape:
            self.drag_shape = shape
            self.dragStartPos = evt.GetPosition()

    def OnLeftUp(self, evt):
        if not self.drag_image or not self.drag_shape:
            self.drag_image = None
            self.drag_shape = None
            return

        # Hide the image, end dragging, and nuke out the drag image.
        self.drag_image.Hide()
        self.drag_image.EndDrag()
        self.drag_image = None

        self.drag_shape.pos = (
            self.drag_shape.pos[0] + evt.GetPosition()[0] - self.dragStartPos[0],
            self.drag_shape.pos[1] + evt.GetPosition()[1] - self.dragStartPos[1]
            )

        self.drag_shape.shown = True
        self.RefreshRect(self.drag_shape.GetRect())
        self.drag_shape = None


    def OnMotion(self, evt):
        # Ignore mouse movement if we're not dragging.
        if not self.drag_shape or not evt.Dragging() or not evt.LeftIsDown():
            return

        # if we have a shape, but haven't started dragging yet
        if self.drag_shape and not self.drag_image:

            # only start the drag after having moved a couple pixels
            tolerance = 2
            pt = evt.GetPosition()
            dx = abs(pt.x - self.dragStartPos.x)
            dy = abs(pt.y - self.dragStartPos.y)
            if dx <= tolerance and dy <= tolerance:
                return

            # refresh the area of the window where the shape was so it
            # will get erased.
            self.drag_shape.shown = False
            self.RefreshRect(self.drag_shape.GetRect(), True)
            self.Update()

            item = self.drag_shape.text if self.drag_shape.text else self.drag_shape.bmp
            self.drag_image = wx.DragImage(item,
                                         wx.Cursor(wx.CURSOR_HAND))

            hotspot = self.dragStartPos - self.drag_shape.pos
            self.drag_image.BeginDrag(hotspot, self, self.drag_shape.fullscreen)

            self.drag_image.Move(pt)
            self.drag_image.Show()

        # if we have shape and image then move it, posibly highlighting another shape.
        elif self.drag_shape and self.drag_image:
            # now move it and show it again if needed
            self.drag_image.Move(evt.GetPosition())


    def OnLeaveWindow(self, evt):
        """On leavewindow event drop dragged image by simulating a left up event."""
        self.OnLeftUp(evt)


    #
    # Bezel Configuration mode
    #
    def start_bezel_config(self):
        """Enters bezel config mode.

        Reveals buttons on each display right and bottom edges
        to allow adding bezels. Additionally hides display
        position config button(s)."""
        # TODO Change background color?
        self.old_bezels = self.display_sys.bezels_in_mm()
        self.bezel_conifg_mode = True
        self.show_bezel_buttons(True)
        # Hide preview positioning config button
        self.toggle_buttons(False, False)

    def bezel_config_save(self):
        """Saves bezel values for the active DisplaySystem."""
        self.bezel_conifg_mode = False
        self.show_bezel_buttons(False)
        # Show preview positioning config button
        self.toggle_buttons(True, False)
        self.full_refresh_preview(True, True, False)
        # trigger a DisplaySystem save.
        self.display_sys.save_system()

    def bezel_config_cancel(self):
        """Exits out of the bezel config mode without saving."""
        self.bezel_conifg_mode = False
        self.show_bezel_buttons(False)
        # Show preview positioning config button
        self.toggle_buttons(True, False)
        self.display_sys.update_bezels(self.old_bezels)
        for pops, bez_mms in zip(self.bezel_popups, self.old_bezels):
            pops[0].set_bezel_value(bez_mms[0])
            pops[1].set_bezel_value(bez_mms[1])
        self.display_data = self.display_sys.get_disp_list(True)
        self.full_refresh_preview(True, True, False)


    def create_bezel_buttons(self):
        # load icons into bitmaps
        rb_png = os.path.join(RESOURCES_PATH, "icons8-merge-vertical-96.png")
        bb_png = os.path.join(RESOURCES_PATH, "icons8-merge-horizontal-96.png")
        rb_img = wx.Image(rb_png, type=wx.BITMAP_TYPE_ANY)
        bb_img = wx.Image(bb_png, type=wx.BITMAP_TYPE_ANY)
        rb_bmp = rb_img.Scale(20, 20).Resize((20, 20), (0, 0)).ConvertToBitmap()
        bb_bmp = bb_img.Scale(20, 20).Resize((20, 20), (0, 0)).ConvertToBitmap()

        # create bitmap buttons
        for st_bmp in self.preview_img_list:
            butts = []
            butt_rb = wx.BitmapButton(self, bitmap=rb_bmp, name="butt_bez_r")
            butt_bb = wx.BitmapButton(self, bitmap=bb_bmp, name="butt_bez_b")
            self.bez_butt_sz = butt_rb.GetSize()
            pos_rb, pos_bb = self.bezel_button_positions(st_bmp)
            butt_rb.SetPosition((pos_rb[0], pos_rb[1]))
            butt_bb.SetPosition((pos_bb[0], pos_bb[1]))
            butt_rb.Bind(wx.EVT_BUTTON, self.onBezelButton)
            butt_bb.Bind(wx.EVT_BUTTON, self.onBezelButton)
            self.bez_buttons.append(
                (
                    butt_rb,
                    butt_bb
                )
            )
        self.show_bezel_buttons(False)
        self.create_bezel_popups()

    def create_bezel_popups(self):
        self.bezel_popups = []
        bezel_mm = self.display_sys.bezels_in_mm()
        for butts, bez_mm in zip(self.bez_buttons, bezel_mm):
            pop_rb = self.popup_at_button(butts[0])
            pop_rb.set_bezel_value(bez_mm[0])
            pop_bb = self.popup_at_button(butts[1])
            pop_bb.set_bezel_value(bez_mm[1])
            self.bezel_popups.append(
                (
                    pop_rb,
                    pop_bb
                )
            )

    def popup_at_button(self, button):
        """Initialize a popup at button position."""
        pop = self.BezelEntryPopup(self, wx.SIMPLE_BORDER)
        return pop

    def move_popup_to_button(self, pop, button):
        """Move pop next to its associated button."""
        butt_name = button.GetName()
        pos = button.ClientToScreen( (0, 0) )
        butt_sz = button.GetSize()
        pop_sz = pop.GetSize()
        if butt_name == "butt_bez_r":
            # Center pop vertically to button
            y_cntr = (- pop_sz[1] + butt_sz[1])/2
            pop.Position(pos, (- pop_sz[0], y_cntr))
        else:
            # Center pop horizontally to button
            x_cntr = (- pop_sz[0] + butt_sz[0])/2
            pop.Position(pos, (x_cntr, - pop_sz[1]))

    def show_bezel_buttons(self, show):
        """Show/Hide the bezel buttons."""
        for butt in self.bez_buttons:
            butt[0].Show(show)
            butt[1].Show(show)

    def bezel_button_positions(self, st_bmp):
        """Return the mid points on the screen of the right and bottom edges
        of the given StaticBitmap."""
        sz = st_bmp.GetSize()
        pos = st_bmp.GetPosition()
        bsz = self.bez_butt_sz
        pos_rb = (sz[0] + pos[0] - bsz[0]/2, sz[1]/2 + pos[1] - bsz[1]/2)
        pos_bb = (sz[0]/2 + pos[0] - bsz[0]/2, sz[1] + pos[1] - bsz[1]/2)
        return [pos_rb, pos_bb]

    def move_bezel_buttons(self):
        """Move bezel buttons after a resize."""
        for butts, st_bmp in zip(self.bez_buttons, self.preview_img_list):
            pos_rb, pos_bb = self.bezel_button_positions(st_bmp)
            butts[0].SetPosition((pos_rb[0], pos_rb[1]))
            butts[1].SetPosition((pos_bb[0], pos_bb[1]))

    def move_bezel_popups(self):
        """Move bezel popups to their respective buttons."""
        for butts, pops in zip(self.bez_buttons, self.bezel_popups):
            self.move_popup_to_button(pops[0], butts[0])
            self.move_popup_to_button(pops[1], butts[1])


    def onBezelButton(self, event):
        self.move_bezel_popups()
        #Get button instance and find it in list
        button = event.GetEventObject()
        for butt_pair in self.bez_buttons:
            if button in butt_pair:
                button_pos = (self.bez_buttons.index(butt_pair), butt_pair.index(button))

        # Pick and show respective popup
        pop = self.bezel_popups[button_pos[0]][button_pos[1]]
        pop.Popup()


    #
    # Bezel entry pop-up
    #

    class BezelEntryPopup(wx.PopupTransientWindow):
        """Adds a bit of text and mouse movement to the wx.PopupWindow"""
        def __init__(self, parent, style):
            wx.PopupTransientWindow.__init__(self, parent, style)
            self.preview = parent
            pnl = wx.Panel(self)
            # pnl.SetBackgroundColour("CADET BLUE")

            st = wx.StaticText(pnl, -1,
                            "Enter the size of adjacent bezels and gap\n"
                            "in millimeters:")
            # self.tc_bez = wx.TextCtrl(pnl, -1, size=(100, -1))
            self.tc_bez = wx.TextCtrl(pnl, -1, style=wx.TE_RIGHT|wx.TE_PROCESS_ENTER)
            self.tc_bez.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
            self.current_bez_val = None
            butt_save = wx.Button(pnl, label="Apply")
            butt_canc = wx.Button(pnl, label="Cancel")
            butt_save.Bind(wx.EVT_BUTTON, self.onApply)
            butt_canc.Bind(wx.EVT_BUTTON, self.onCancel)
            butt_sizer = wx.BoxSizer(wx.HORIZONTAL)
            # butt_sizer.AddStretchSpacer()
            butt_sizer.Add(self.tc_bez, 0, wx.ALL, 5)
            butt_sizer.Add(butt_save, 0, wx.ALL, 5)
            butt_sizer.Add(butt_canc, 0, wx.ALL, 5)

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(st, 0, wx.ALL, 5)
            # sizer.Add(self.tc_bez, 0, wx.ALL, 5)
            sizer.Add(butt_sizer, 0, wx.ALL|wx.EXPAND, 0)
            pnl.SetSizer(sizer)

            sizer.Fit(pnl)
            sizer.Fit(self)
            self.Layout()

        def ProcessLeftDown(self, evt):
            return wx.PopupTransientWindow.ProcessLeftDown(self, evt)

        def OnEnter(self, evt):
            """Bind pressing Enter in the txtctrl to apply entered value."""
            self.onApply(evt)

        def OnDismiss(self):
            self.onCancel(None)

        def onApply(self, event):
            entered_val = self.test_bezel_value()
            if entered_val is False:
                # Abort applying and alert user but don't
                # Dismiss popup to fascilitate fixing.
                msg = ("Bezel thickness must be a non-negative number, "
                       "'{}' was entered.".format(self.tc_bez.GetValue()))
                sp_logging.G_LOGGER.info(msg)
                self.Hide()
                dial = wx.MessageDialog(self, msg, "Error", wx.OK|wx.STAY_ON_TOP|wx.CENTRE)
                dial.ShowModal()
                self.Show()
                return -1
            self.current_bez_val = entered_val
            display_sys = self.preview.display_sys
            pops = self.preview.bezel_popups
            bezel_mms = []
            for pop_pair in pops:
                bezel_mms.append(
                    (
                        pop_pair[0].bezel_value(),
                        pop_pair[1].bezel_value()
                    )
                )
            self.Dismiss()
            # propagate values and refresh preview
            self.preview.display_sys.update_bezels(bezel_mms)
            self.preview.display_data = self.preview.display_sys.get_disp_list(True)
            self.preview.full_refresh_preview(True, True, False)

        def onCancel(self, event):
            if self.current_bez_val:
                self.tc_bez.SetValue(str(self.current_bez_val))
            else:
                self.tc_bez.SetValue("0.0")
            self.Dismiss()

        def bezel_value(self):
            """Return the entered bezel thickness as a float."""
            bez = self.tc_bez.GetValue()
            return float(bez)

        def set_bezel_value(self, val):
            """Write val to TextCtrl."""
            self.tc_bez.SetValue(str(val))
            self.current_bez_val = str(val)

        def test_bezel_value(self):
            """Test that entered value in tc_bez is valid and return it."""
            val = self.tc_bez.GetValue()
            try:
                num = float(val)
                if num >= 0:
                    return num
                else:
                    return False
            except ValueError:
                return False
