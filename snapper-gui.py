#!/usr/bin/env python

import dbus
from gi.repository import Gtk, Gdk#, GObject
from time import gmtime, strftime, localtime
from pwd import getpwuid
import subprocess

bus = dbus.SystemBus()
snapper = dbus.Interface(bus.get_object('org.opensuse.Snapper', '/org/opensuse/Snapper'),
							dbus_interface='org.opensuse.Snapper')

class propertiesDialog(Gtk.Dialog):
	"""docstring for propertiesDialog"""
	def __init__(self,parent):
		Gtk.Dialog.__init__(self, "Properties", parent, 0,
			(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))

		# key : value = [widget, grid line]
		widgets = {
		"SUBVOLUME": [Gtk.Label, 0],
		"FSTYPE" : [Gtk.Label, 1],
		"ALLOW_USERS" : [Gtk.Label, 2],
		"ALLOW_GROUPS" : [Gtk.Label, 3],
		"TIMELINE_CREATE" : [Gtk.Switch, 4],
		"TIMELINE_CLEANUP" : [Gtk.Switch, 5],
		"TIMELINE_LIMIT_HOURLY" : [Gtk.SpinButton, 6],
		"TIMELINE_LIMIT_DAILY" : [Gtk.SpinButton, 7],
		"TIMELINE_LIMIT_MONTHLY" : [Gtk.SpinButton, 8],
		"TIMELINE_LIMIT_YEARLY" : [Gtk.SpinButton, 9],
		"TIMELINE_MIN_AGE" : [Gtk.SpinButton, 10],
		"EMPTY_PRE_POST_CLEANUP" : [Gtk.Switch, 11],
		"EMPTY_PRE_POST_MIN_AGE" :  [Gtk.SpinButton, 12],
		"NUMBER_LIMIT" : [Gtk.SpinButton, 13],
		"NUMBER_MIN_AGE" : [Gtk.SpinButton, 14],
		"NUMBER_CLEANUP" : [Gtk.Switch, 15],
		"BACKGROUND_COMPARISON" : [Gtk.Switch, 16]
		}
		notebook = Gtk.Notebook()
		self.get_content_area().pack_start(notebook, True, True, 0)
		for aux, config in enumerate(snapper.ListConfigs()):
			# VerticalBox to hold a label and the grid
			vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
			vbox.pack_start(Gtk.Label("Subvolume to snapshot: " + config[1]),False,False,0)
			# Grig to hold de pairs key and value
			grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
			vbox.pack_start(grid,True,True,0)

			for k, v in config[2].items():
				label = Gtk.Label(k,selectable=True)
				grid.attach(label, 0, widgets[k][1], 1, 1)

				if widgets[k][0] == Gtk.Label:
					grid.attach_next_to(widgets[k][0](v,selectable=True),label, Gtk.PositionType.RIGHT, 1, 1)
				elif widgets[k][0] == Gtk.SpinButton:
					adjustment = Gtk.Adjustment(0, 0, 5000, 1, 10, 0)
					spinbutton = widgets[k][0](adjustment=adjustment)
					spinbutton.set_value(int(v))
					grid.attach_next_to(spinbutton,label, Gtk.PositionType.RIGHT, 1, 1)
				elif widgets[k][0] == Gtk.Switch:
					switch = widgets[k][0]()
					if v == "yes":
						switch.set_active(True)
					elif v == "no":
						switch.set_active(False)
					grid.attach_next_to(switch,label, Gtk.PositionType.RIGHT, 1, 1)
			# add a new page to the notebook with the name of the config and the content
			notebook.append_page(vbox, Gtk.Label.new(config[0]))
		notebook.show_all()


class deleteDialog(object):
	"""docstring for deleteDialog"""
	def __init__(self, parent, config, snapshots):
		super(deleteDialog, self).__init__()
		builder = Gtk.Builder()
		builder.add_from_file("glade/deleteSnapshot.glade")
		
		self.dialog = builder.get_object("dialogDelete")
		self.dialog.set_transient_for(parent)
		self.deletetreeview = builder.get_object("deletetreeview")
		builder.connect_signals(self)

		self.deleteTreeStore = Gtk.ListStore(bool, int, str,  str)
		for snapshot in snapshots:
			snapinfo = snapper.GetSnapshot(config,snapshot)
			self.deleteTreeStore.append([True, snapinfo[0], getpwuid(snapinfo[4])[0], snapinfo[5]])
		self.deletetreeview.set_model(self.deleteTreeStore)

		response = self.dialog.run()
		self.dialog.hide()
		delete = []
		# Check if any of the selected snapshots was toggled
		for (aux,snapshot) in enumerate(snapshots):
			if self.deleteTreeStore[aux][0]:
				delete.append(snapshot)

		if response == Gtk.ResponseType.YES and len(delete) != 0:
			snapper.DeleteSnapshots(config, delete)
			self.deleted = delete
		else:
			self.deleted = []

	def on_toggle_delete_snapshot(self,widget,index):
		self.deleteTreeStore[int(index)][0] = not(self.deleteTreeStore[int(index)][0])
		pass

class SnapperGUI(object):
	"""docstring for SnapperGUI"""
	def __init__(self):
		super(SnapperGUI, self).__init__()
		self.builder = Gtk.Builder()
		self.builder.add_from_file("glade/mainWindow.glade")
		self.builder.connect_signals(self)
		self.mainWindow = self.builder.get_object("mainWindow")

		self.currentConfig = "root"
		self.init_configs_menuitem()

		self.statusbar = self.builder.get_object("statusbar")
		self.snapshotsTreeView = self.builder.get_object("snapstreeview")
		#self.configsTreeView = self.builder.get_object("configstreeview")
		#self.update_configs_list()
		self.update_snapshots_list()

		self.dialogCreate = self.builder.get_object("dialogCreate")

	def update_snapshots_list(self,widget=None):
		treestore = self.get_config_treestore(self.currentConfig)
		if treestore == None:
			self.builder.get_object("configActions").set_sensitive(False)
		else:
			self.builder.get_object("configActions").set_sensitive(True)
		self.snapshotsTreeView.set_model(treestore)
		self.snapshotsTreeView.expand_all()

	#NOT USED delete in the future
	def update_configs_list(self):
		liststore = Gtk.ListStore(str)
		for config in snapper.ListConfigs():
			liststore.append([config[0]])
		self.configsTreeView.get_selection().select_path(0)
		self.configsTreeView.set_model(liststore)

	def init_configs_menuitem(self):
		menu = self.builder.get_object("filemenu")
		radioitem = None
		for aux, config in enumerate(snapper.ListConfigs()):
			radioitem = Gtk.RadioMenuItem(label=config[0],group=radioitem)
			menu.insert(radioitem,5+aux)
			radioitem.show()
			radioitem.connect("toggled", self.on_menu_config_changed)


	def get_config_treestore(self,config):
		configstree = Gtk.TreeStore(int, int, int, str, str, str, str)
		# Get from DBus all the snappshots for this configuration
		try:
			snapshots_list = snapper.ListSnapshots(config)
		except dbus.exceptions.DBusException:
			dialog = Gtk.MessageDialog(self.mainWindow, 0, Gtk.MessageType.ERROR,
			Gtk.ButtonsType.OK, "This user does not have permission to edit this configuration")
			dialog.run()
			dialog.destroy()
			return None
		parents = []
		self.statusbar.push(5,"%d snapshots"% (len(snapshots_list)))
		for snapshot in snapshots_list:
			if (snapshot[1] == 1): # Pre Snapshot
				parents.append(configstree.append(None , self.snapshot_columns(snapshot)))
			elif (snapshot[1] == 2): # Post snappshot
				for parent in parents:
					if (configstree.get_value(parent, 0) == snapshot[2]):
						configstree.append(parent , self.snapshot_columns(snapshot))
						break
				if (configstree.get_value(parent, 0) != snapshot[2]):
					configstree.append(None , self.snapshot_columns(snapshot))
			else:  # Single snapshot
				configstree.append(None , self.snapshot_columns(snapshot))
		return configstree

	def snapshot_columns(self,snapshot):
		if(snapshot[3] == -1):
			date = "Now"
		else:
			date = strftime("%a %R %e/%m/%Y", localtime(snapshot[3]))
		return [snapshot[0], snapshot[1], snapshot[2], date, getpwuid(snapshot[4])[0], snapshot[5], snapshot[6]]

	def add_snapshot_to_tree(self, snapshot, pre_snapshot=None):
		treemodel = self.snapshotsTreeView.get_model()
		for aux, row in enumerate(treemodel):
			if(pre_snapshot == str(row[0])):
				pass
		snapinfo = snapper.GetSnapshot(self.currentConfig, snapshot)
		treemodel.append(pre_snapshot, self.snapshot_columns(snapinfo))

	def remove_snapshot_from_tree(self, snapshot):
		# TODO Check if this row has any childs
		treemodel = self.snapshotsTreeView.get_model()
		for aux, row in enumerate(treemodel):
			if(snapshot == row[0]):
				del treemodel[aux]

	def on_button_press_event(self, widget, event):
		# Check if right mouse button was preseed
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
			popup = self.builder.get_object("popupSnapshots")
			popup.popup(None, None, None, None, event.button, event.time)
			return False

	def on_popup(self,widget):
		popup = self.builder.get_object("popupSnapshots")
		popup.popup(None,None,None,None,0,0)

	def on_snapshots_selection_changed(self,selection):
		(model, paths) = selection.get_selected_rows()
		if(len(paths) == 0):
			self.builder.get_object("snapshotActions").set_sensitive(False)
		else:
			self.builder.get_object("snapshotActions").set_sensitive(True)

	def on_menu_config_changed(self,widget):
		if(widget.get_active()):
			self.currentConfig = widget.get_label()
			self.update_snapshots_list()

	def on_view_item_column_toggled(self,widget):
		widget.set_visible(not(widget.get_visible()))

	def on_toolbar_style_change(self,widget):
		toolbar = self.builder.get_object("toolbar1")
		if(widget.get_active()):
			toolbar.set_style(widget.get_current_value())

	def on_view_item_toolbar_toggled(self,widget):
		toolbar = self.builder.get_object("toolbar1")
		if(widget.get_active()):
			toolbar.show()
		else:
			toolbar.hide()

	#NOT USED delete in the future
	def on_configstreeview_changed(self,selection):
		model, treeiter = selection.get_selected()
		if treeiter != 0 and model != None:
			self.currentConfig = model[treeiter][0]
			print(self.currentConfig)
			self.update_snapshots_list()

	def on_create_snapshot(self, widget):
		response = self.dialogCreate.run()
		if response == Gtk.ResponseType.OK:
			newSnapshot = snapper.CreateSingleSnapshot(self.currentConfig, 
										"snapper test", 
										"", 
										{"by":"SnapperGUI"})
			self.add_snapshot_to_tree(newSnapshot)
			# snapshot = snapper.GetSnapshot(currentConfig,newSnapshot)
			print("Created single snapshot for " + self.currentConfig)
		elif response == Gtk.ResponseType.CANCEL:
			print("The Cancel button was clicked")
		self.dialogCreate.hide()


	def on_delete_snapshot(self, selection):
		(model, paths) = selection.get_selected_rows()
		snapshots = []
		for path in paths:
			treeiter = model.get_iter(path)
			snapshots.append(model[treeiter][0])
		dialog = deleteDialog(self.mainWindow, self.currentConfig,snapshots)
		for snapshot in dialog.deleted:
			self.remove_snapshot_from_tree(snapshot)
		if(len(dialog.deleted) != 0):
			self.statusbar.push(True, "Snapshots deleted from %s: %s"% (self.currentConfig, dialog.deleted))

	def on_open_snapshot_folder(self, selection,treepath=None,column=None):
		model, paths = selection.get_selected_rows()
		for path in paths:
			treeiter = model.get_iter(path)
			mountpoint = snapper.GetMountPoint(self.currentConfig, model[treeiter][0])
			subprocess.Popen(['xdg-open', mountpoint])
			self.statusbar.push(True, 
				"The mount point for the snapshot %s from %s is %s"% 
				(model[treeiter][0], self.currentConfig, mountpoint))


	def on_configs_properties_clicked(self,notebook):
		dialog = propertiesDialog(self.mainWindow)
		dialog.run()
		dialog.destroy()

	def on_about_clicked(self,widget):
		about = self.builder.get_object("aboutdialog1")
		about.run()
		about.hide()

	def delete_event(self,widget):
		Gtk.main_quit()

	def main(self):
		self.mainWindow.show()
		Gtk.main()
		return 0

def dbus_signal_handler():
	pass

if __name__ == '__main__':
	interface = SnapperGUI()
	interface.main()