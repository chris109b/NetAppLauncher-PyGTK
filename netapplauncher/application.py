#!/usr/bin/env python3

# Python standard library imports
import weakref
import subprocess
import json
import urllib
# Imports from external modules
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf, PixbufLoader
from zeroconf import ServiceBrowser, Zeroconf
# Internal modules import
from .mainwindow import MainWindow


class ZeroconfBrowserDelegate:

    def is_service_valid(self, info):
        raise NotImplementedError


class ZeroconfListener(object):

    def __init__(self, browser):
        self.__browser_ref = weakref.ref(browser)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        self.__browser_ref().add_service(info)

    def remove_service(self, _, service_type, name):
        self.__browser_ref().remove_service(service_type, name)


class Application:

    DEFAULT_ENCODING = "utf-8"
    SERVICE_TYPE_HTTP = "_http._tcp.local."
    KEY_WEB_APP_INFO_PATH = "net_app_info_path"
    KEY_WEB_APP_VENDOR_UUID = "net_app_vendor_uuid"

    COLUMN_PIXEL_BUFFER = 0
    COLUMN_NAME_LABEL = 1
    COLUMN_IDENTIFIER = 2

    def __init__(self):

        self.__zeroconf = None
        self.__listener = None
        self.__browser = None
        self.__service_dict = {}
        self.__net_app_dict = {}
        self.__is_visible = False

        self.__main_window = MainWindow()
        self.__main_window.connect("delete-event", self.on_close_button_clicked)

        self.net_apps_list_store = Gtk.ListStore(Pixbuf, str, str)
        self.__main_window.icon_view.set_model(self.net_apps_list_store)
        self.__main_window.icon_view.set_pixbuf_column(0)
        self.__main_window.icon_view.set_text_column(1)
        self.__main_window.icon_view.connect("item-activated", self.on_item_activated, self.net_apps_list_store)
        # for i in range(0, 2):
        #    pixel_buffer = Gtk.IconTheme.get_default().load_icon("package-x-generic", 64, 0)
        #    self.net_apps_list_store.append([pixel_buffer, "Name label", "identifier"])

    # MARK: Application live cycle

    def start(self):
        protocol = self.SERVICE_TYPE_HTTP
        self.__zeroconf = Zeroconf()
        self.__listener = ZeroconfListener(self)
        self.__browser = ServiceBrowser(self.__zeroconf, protocol, self.__listener)

        self.__main_window.show_all()
        self.__is_visible = True
        Gtk.main()

    def stop(self):
        self.__zeroconf.close()
        self.__zeroconf = None
        self.__listener = None
        self.__browser = None
        Gtk.main_quit()

    def show_main_window(self):
        if self.__is_visible is False:
            self.__main_window.show()
            self.__is_visible = True

    def hide_main_window(self):
        if self.__is_visible is True:
            self.__main_window.hide()
            self.__is_visible = False

    # MARK: Zeroconf interface

    @classmethod
    def find_list_entry_by_name(cls, model, path, iterator, data):
        if model.get_value(iterator, cls.COLUMN_IDENTIFIER) == data["name"]:
            data["iter"] = iterator
            return True
        else:
            return False

    def add_service(self, info):
        if info is None:
            return
        display_name = info.name[:-(len(self.SERVICE_TYPE_HTTP) + 1)]
        self.__service_dict[info.name] = info
        pixel_buffer = Gtk.IconTheme.get_default().load_icon("package-x-generic", 64, 0)
        self.net_apps_list_store.append([pixel_buffer, display_name, info.name])
        self.resolve_service(info)

    def download_app_link_resources(self, info, info_uri, info_path):
        ipv4_address = '.'.join(map(str, info.address))
        info_directory = '/'.join(info_path[1:].split('/')[:-1])
        info_directory = '/' + info_directory if len(info_directory) > 0 else info_directory
        port = info.port
        with urllib.request.urlopen(info_uri) as info_response:
            json_string = info_response.read().decode(self.DEFAULT_ENCODING)
            try:
                app_info_dict = json.loads(json_string)
            except json.decoder.JSONDecodeError as e:
                print("Could not decode JSON")
                print(json_string)
                print(e)
                return
            self.__net_app_dict[info.name] = app_info_dict
            icon_file = app_info_dict["icon"]["64"]
            app_name = app_info_dict["info"]["app_name"]
            self.update_list_store_element(info.name, name_label=app_name)
            try:
                loader = PixbufLoader()
                icon_uri = "http://{0}:{1}{2}/{3}".format(ipv4_address, port, info_directory, icon_file)
                response = urllib.request.urlopen(icon_uri)
                loader.write(response.read())
                loader.close()
                self.update_list_store_element(info.name, pixel_buffer=loader.get_pixbuf())
            except:
                print("Could not load image:", icon_uri)

    def resolve_service(self, info):
        ipv4_address = '.'.join(map(str, info.address))
        port = info.port
        try:
            info_path = info.properties[self.KEY_WEB_APP_INFO_PATH.encode()].decode(self.DEFAULT_ENCODING)
        except KeyError:
            print(info.name, "is not a NetApp:", info)
        else:
            info_path = "/" + info_path if info_path[0] != "/" else info_path
            info_uri = "http://{0}:{1}{2}".format(ipv4_address, port, info_path)
            try:
                self.download_app_link_resources(info, info_uri, info_path)
            except urllib.error.HTTPError as e:
                print("Could not download resources", info_uri, e)
            except urllib.error.URLError as e:
                print("Could not download resources", info_uri, e)

    def update_list_store_element(self, name, name_label=None, pixel_buffer=None):
        data = {"name": name, "iter": None}
        self.net_apps_list_store.foreach(self.find_list_entry_by_name, data)
        if data["iter"] is not None:
            if name_label is not None:
                self.net_apps_list_store.set_value(data["iter"], self.COLUMN_NAME_LABEL, name_label)
            if pixel_buffer is not None:
                self.net_apps_list_store.set_value(data["iter"], self.COLUMN_PIXEL_BUFFER, pixel_buffer)

    def remove_service(self, _, name):
        data = {"name": name, "iter": None}
        self.net_apps_list_store.foreach(self.find_list_entry_by_name, data)
        if data["iter"] is not None:
            self.net_apps_list_store.remove(data["iter"])
        del(self.__service_dict[name])
        del(self.__net_app_dict[name])

    # MARK: User interface

    def on_item_activated(self, icon_view, tree_path, store):
        name = store.get_value(store.get_iter(tree_path), self.COLUMN_IDENTIFIER)
        info = self.__service_dict[name]
        ipv4_address = '.'.join(map(str, info.address))
        port = info.port
        display_uri = "http://{0}:{1}/".format(ipv4_address, port)
        command = ["xdg-open", display_uri]
        subprocess.call(command)
        print(info)
        icon_view.unselect_all()
        self.hide_main_window()

    def on_close_button_clicked(self, widget, args):
        self.stop()






