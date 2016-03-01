import time, datetime
import logging
import urllib, urllib2
import os
import sqlite3

import edutils
import ijson
# from Finder.Finder_items import item
import threading
from __builtin__ import False
import edevent

class StarMapDbUpdatedEvent(edevent.BaseEvent):
    def __init__(self):
        edevent.BaseEvent.__init__(self, "StarMapUpdated", datetime.datetime.now())
    
    def _fill_json_dict(self, json_dict):
        pass
    
class DbInfo(object):
    TABLE_NAME = 'DbInfo'
    ID = "_id"
    COLUMN_NAME_CONFIG = "ConfigName";
    COLUMN_NAME_VALUE = "Value";

    CONFIG_NAME_LAST_EDSM_CHECK = "LastEDSMCheck";

class EDSMSystems(object):
    TABLE_NAME = "EDSMSystems";
    ID = "_id"
    COLUMN_NAME_SYSTEM = "System";
    COLUMN_NAME_XCOORD = "xCoord";
    COLUMN_NAME_YCOORD = "yCoord";
    COLUMN_NAME_ZCOORD = "zCoord";

class EDSMDistances(object):
    TABLE_NAME = "EDSMDistances";
    ID = "_id"
    COLUMN_NAME_FROM = "FromSystem";
    COLUMN_NAME_TO = "ToSystem";
    COLUMN_NAME_DISTANCE = "Distance";
    COLUMN_NAME_DATE = "SubmitDate";

class EDSMSystem(object):
    def __init__(self, row):
        self.id = row[0]
        self.name = row[1]
        
        if row[2] == None:
            self.position = None
        else:
            self.position = (row[2], row[3], row[4])
        
    def __str__(self, *args, **kwargs):
        return "EDSMSystems [id: %d, name: %s, coord: %s]" % (self.id, self.name, str(self.position))

class EDSMDistance(object):
    def __init__(self, rowId, sys1, sys2, distance, date):
        self.id = rowId
        self.sys1 = sys1
        self.sys2 = sys2
        self.distance = distance
        self.date = date
        
    def __str__(self, *args, **kwargs):
        return "EDSMDistance [id: %d, sys1: %s, sys2: %s, distance: %f, date: %s]" % (self.id, self.sys1, self.sys2, self.distance, self.date)

    def __eq__(self, other):
        if not isinstance(other, EDSMDistance):
            return False
        
        return self.sys1 == other.sys1 and self.sys2 == other.sys2
    
    def __ne__(self, other):
        if not isinstance(other, EDSMDistance):
            return True
        
        return self.sys1 != other.sys1 or self.sys2 != other.sys2
    
    def __hash__(self):
        return hash("%s:%s" % (self.sys1, self.sys2))
    
class EDSMDb(object):
    def __init__(self):
        self._log = logging.getLogger("com.fussyware.edproxy")

        edproxy_db_dir = edutils.get_database_dir()
        edproxy_db_filename = os.path.join(edproxy_db_dir, "edsm.db")
        
        self._first_time_install = False
        self._dbconn = None
        
        self._update_event = threading.Event()
        self._background_update_running = False
        
        if (not os.path.exists(edproxy_db_dir)):
            os.makedirs(edproxy_db_dir)
            
        if (not os.path.exists(edproxy_db_filename)):
            self.__do_create_db(edproxy_db_filename)
        else:
            self._dbconn = sqlite3.connect(edproxy_db_filename, check_same_thread=False)

    def close(self):
        self.stop_background_update()
        self._dbconn.close()
        
    def update(self, onprogress = None):
        updated = False
        
        if self._first_time_install:
            # Go back in time by a day so that we absolutely do not miss anything
            # from when the database was first created.
            last_check = self.__get_utc(days = -1)
            
            self.__pull_systems(onprogress)
            self.__pull_distances(onprogress)
            self.__setup_info(last_check)
                    
            self._first_time_install = False
            updated = True
        else:
            self.__update_edsm(onprogress)
        
        return updated
    
    def start_background_update(self, onupdate = None):
        self._background_update_running = True
        
        _thread = threading.Thread(target = self.__background_updater, args = (onupdate,))
        _thread.daemon = True
        _thread.start()

    def stop_background_update(self):
        self._background_update_running = False
        self._update_event.set()
        
    def get_system(self, name):
        cursor = None
        try:
            cursor = self._dbconn.cursor()
            
            # TODO: This does NOT handle the case where we have duplicate systems!
            sql = "SELECT * FROM %s WHERE %s=? LIMIT 1" % (EDSMSystems.TABLE_NAME, EDSMSystems.COLUMN_NAME_SYSTEM)
            cursor.execute(sql, (name,))
            row = cursor.fetchone()
            
            if row:
                return EDSMSystem(row)
            else:
                return None
        except sqlite3.Error, e:
            self._log.error("EDSM get system: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()

    def get_distances(self, system):
        lower_system = system.lower()
        sys1 = self.get_system(system)
        cursor = None
        
        try:
            cursor = self._dbconn.cursor()
            dist_list = set()
            
            sql = "SELECT * FROM %s WHERE %s=? OR %s=?" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO)
            cursor.execute(sql, (system, system))
            row = cursor.fetchone()
            
            while row:
                if row[1] and row[2]:
                    _id = row[0]
                    
                    if lower_system == row[1].lower(): 
                        sys2 = self.get_system(row[2])
                    else:
                        sys2 = self.get_system(row[1])
                        
                    if sys2:
                        dist = EDSMDistance(_id, sys1, sys2, row[3], self.__get_datetime(timestamp = row[4]))
                        if not dist in dist_list:
                            dist_list.add(dist)
                            
                            if len(dist_list) == 25:
                                break
                    
                row = cursor.fetchone()
                            
            return dist_list
        except sqlite3.Error, e:
            self._log.error("EDSM get system: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()
                
    def get_distance(self, sys1, sys2):
        cursor = None
        try:
            cursor = self._dbconn.cursor()
            
            sql = "SELECT * FROM %s WHERE %s IN (?,?) AND %s IN (?,?) LIMIT 1" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO)
            cursor.execute(sql, (sys1, sys2, sys1, sys2))
            row = cursor.fetchone()

            if row:
                return EDSMDistance(row[0], row[1], row[2], row[3], self.__get_datetime(timestamp = row[4]))
            else:
                return None
        except sqlite3.Error, e:
            self._log.error("EDSM get system: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()
                
    def __get_utc(self, dt = None, days = 0):
        if not dt:
            dt = datetime.datetime.utcnow()
            
        if days > 0:
            dt = dt + datetime.timedelta(days = days)
        elif days < 0:
            dt = dt - datetime.timedelta(days = -days)
        
        return int((dt - datetime.datetime(1970, 1, 1)).total_seconds() * 1000.0)
    
    def __get_datetime(self, timestamp = None, timestring = None):
        if timestring != None:
            return datetime.datetime.strptime(timestring, "%Y-%m-%d %H:%M:%S")
        elif timestamp != None:
            return datetime.datetime.utcfromtimestamp(float(timestamp) / 1000.0)
        else:
            return datetime.datetime.utcnow()

    def __update_last_check(self, cursor, timestamp):
        sql = "UPDATE %s SET %s=? WHERE %s=?" % (DbInfo.TABLE_NAME, DbInfo.COLUMN_NAME_VALUE, DbInfo.COLUMN_NAME_CONFIG) 
        
        cursor.execute(sql, (timestamp, DbInfo.CONFIG_NAME_LAST_EDSM_CHECK))
        
        self._dbconn.commit()
        
    def __background_updater(self, onupdate):
        while self._background_update_running:
            if not self._update_event.wait(timeout = (5 * 60)):
                if self._background_update_running and self.__update_edsm() and onupdate:
                    onupdate()
                
            self._update_event.clear()
        
    def __update_edsm(self, onprogress = None):
        cursor = None
        updated = False
        
        try:
            cursor = self._dbconn.cursor()

            sql = "SELECT %s FROM %s WHERE %s=?" % (DbInfo.COLUMN_NAME_VALUE, DbInfo.TABLE_NAME, DbInfo.COLUMN_NAME_CONFIG)
            cursor.execute(sql, (DbInfo.CONFIG_NAME_LAST_EDSM_CHECK,))
            
            now = datetime.datetime.utcnow()
            start_time = self.__get_datetime(int(cursor.fetchone()[0]))
            end_time = start_time + datetime.timedelta(days = 14)
            end_time = min(end_time, now)
            
            while start_time != now:
                query_params= dict()
                query_params["startdatetime"] = start_time.strftime("%Y-%m-%d %H:%M:%S +00:00") 
                query_params["enddatetime"] = end_time.strftime("%Y-%m-%d %H:%M:%S +00:00")
                query_params["coords"] = "1"
                query_params["known"] = "1"
                query_params["showId"] = "1"

                url = "http://www.edsm.net/api-v1/systems?%s" % (urllib.urlencode(query_params))
                request = urllib2.Request(url)
                request.add_header("Accept-Encoding", "")
                request.add_header("Content-Type", "application/json")
                request.add_header("charset", "utf-8")

                self._log.debug(url)
                if onprogress:
                    onprogress("Updating EDSM Database - Downloading Systems...")

                self._log.debug("Update Systems...")
                handle = urllib2.urlopen(request)
                if handle:
                    query_sql = "SELECT * FROM %s WHERE %s=? LIMIT 1" % (EDSMSystems.TABLE_NAME, EDSMSystems.ID)
                    update_sql = "UPDATE %s SET %s=?, %s=?, %s=? WHERE %s=?" % (EDSMSystems.TABLE_NAME, EDSMSystems.COLUMN_NAME_XCOORD, EDSMSystems.COLUMN_NAME_YCOORD, EDSMSystems.COLUMN_NAME_ZCOORD, EDSMSystems.ID)
                    insert_sql = "INSERT INTO %s VALUES (?, ?, ?, ?, ?)" % (EDSMSystems.TABLE_NAME)
                    
                    count = 0
                    for item in ijson.items(handle, 'item'):
                        count = count + 1
                        if (count % 100) == 0:
                            if onprogress:
                                onprogress("Updating EDSM Database - Processed [%d] Systems..." % count)
                        
                        _id = int(item["id"])
                        name = item['name']
                        
                        x = y = z = None
                        
                        if 'coords' in item:
                            coords = item['coords']
                            
                            if 'x' in coords:
                                x = float(coords['x'])
                                y = float(coords['y'])
                                z = float(coords['z'])
                
                        cursor.execute(query_sql, (_id,))
                        row = cursor.fetchone()
                        if row:
                            xr = row[2]
                            yr = row[3]
                            zr = row[4]
                            
                            if x != xr or y != yr or z != zr:
                                cursor.execute(update_sql, (x, y, z, _id))
                                updated = True
                        else:
                            cursor.execute(insert_sql, (_id, name, x, y, z))
                            updated = True
                        
                    self._dbconn.commit()
                    self._log.debug("Updated [%d] systems" % (count))
                    
                query_params= dict()
                query_params["startdatetime"] = start_time.strftime("%Y-%m-%d %H:%M:%S +00:00") 
                query_params["enddatetime"] = end_time.strftime("%Y-%m-%d %H:%M:%S +00:00")
                query_params["submitted"] = "1"

                url = "http://www.edsm.net/api-v1/distances?%s" % (urllib.urlencode(query_params))
                request = urllib2.Request(url)
                request.add_header("Accept-Encoding", "")
                request.add_header("Content-Type", "application/json")
                request.add_header("charset", "utf-8")

                if onprogress:
                    onprogress("Updating EDSM Database - Downloading Distances...")

                self._log.debug("Update distances...")
                handle = urllib2.urlopen(request)
                if handle:
                    query_sql = "SELECT * FROM %s WHERE %s IN (?,?) AND %s IN (?,?) LIMIT 1" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO)
                    update_sql = "UPDATE %s SET %s=?, %s=? WHERE %s IN (?,?) AND %s IN (?,?)" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_DISTANCE, EDSMDistances.COLUMN_NAME_DATE, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO)
                    insert_sql = "INSERT INTO %s (%s, %s, %s, %s) VALUES (?, ?, ?, ?)" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO, EDSMDistances.COLUMN_NAME_DISTANCE, EDSMDistances.COLUMN_NAME_DATE)
                     
                    count = 0
                    for item in ijson.items(handle, 'item'):
                        count = count + 1
                        if (count % 100) == 0:
                            if onprogress:
                                onprogress("Updating EDSM Database - Processed [%d] Distances..." % count)
                        
                        _from = item['sys1']['name']
                        _to = item['sys2']['name']
                        _dist = float(item['distance'])

                        _date = self.__get_datetime(timestring = item['date'])
                        _date = self.__get_utc(dt = _date)

                        cursor.execute(query_sql, (_from, _to, _from, _to))
                        row = cursor.fetchone()
                        if row:
                            if _dist != row[3] and _date >= row[4]:
                                cursor.execute(update_sql, (_dist, _date, _from, _to, _from, _to))
                                updated = True
                        else:
                            cursor.execute(insert_sql, (_from, _to, _dist, _date))
                            updated = True
                        
                    self._dbconn.commit()
                    self._log.debug("Updated [%d] distances" % (count))

                start_time = end_time
                end_time = start_time + datetime.timedelta(days = 14)
                end_time = min(end_time, now)
                
                self.__update_last_check(cursor, self.__get_utc(dt = start_time))
        except sqlite3.Error, e:
            self._log.error("EDSM Update: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()
                
        return updated
            
    def __do_create_db(self, filename):
        self._first_time_install = True
        
        cursor = None
        
        try:
            self._dbconn = sqlite3.connect(filename, check_same_thread=False)
            cursor = self._dbconn.cursor()

            self._log.debug("Create EDSM Db")
            cursor.execute("DROP INDEX IF EXISTS EDSMSystemIndex")
            cursor.execute("DROP INDEX IF EXISTS EDSMDistIndex")
            cursor.execute("DROP TABLE IF EXISTS %s" % EDSMSystems.TABLE_NAME)
            cursor.execute("DROP TABLE IF EXISTS %s" % EDSMDistances.TABLE_NAME)
            cursor.execute("DROP TABLE IF EXISTS %s" % DbInfo.TABLE_NAME)
        
            sql = "CREATE TABLE %s (%s INTEGER PRIMARY KEY, %s TEXT COLLATE NOCASE, %s DOUBLE, %s DOUBLE, %s DOUBLE)" % (EDSMSystems.TABLE_NAME, EDSMSystems.ID, EDSMSystems.COLUMN_NAME_SYSTEM, EDSMSystems.COLUMN_NAME_XCOORD, EDSMSystems.COLUMN_NAME_YCOORD, EDSMSystems.COLUMN_NAME_ZCOORD)
            cursor.execute(sql)
        
            sql = "CREATE TABLE %s (%s INTEGER PRIMARY KEY, %s TEXT COLLATE NOCASE, %s TEXT COLLATE NOCASE, %s DOUBLE, %s INTEGER)" % (EDSMDistances.TABLE_NAME, EDSMDistances.ID, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO, EDSMDistances.COLUMN_NAME_DISTANCE, EDSMDistances.COLUMN_NAME_DATE)
            cursor.execute(sql)
        
            sql = "CREATE TABLE %s (%s INTEGER PRIMARY KEY, %s TEXT, %s TEXT)" % (DbInfo.TABLE_NAME, DbInfo.ID, DbInfo.COLUMN_NAME_CONFIG, DbInfo.COLUMN_NAME_VALUE)
            cursor.execute(sql)
        except sqlite3.Error, e:
            self._log.error("Failed creating the EDSM database." + e.args[0])
        finally:
            if cursor:
                cursor.close()
            
    def __pull_systems(self, onprogress = None):
        cursor = None
        
        try:
            if onprogress:
                onprogress("Create EDSM Database - Downloading Systems Nightly...")
                
            cursor = self._dbconn.cursor()
            handle = urllib2.urlopen("http://www.edsm.net/dump/systemsWithCoordinates.json", timeout = 60)
    
            if handle:
                sql = "INSERT INTO %s VALUES (?, ?, ?, ?, ?)" % (EDSMSystems.TABLE_NAME)

                count = 0
                for system in ijson.items(handle, 'item'):
                    count = count + 1
                    if (count % 100) == 0:
                        if onprogress:
                            onprogress("Create EDSM Database - Processed [%d] Systems..." % count)
                        
                    _id = int(system["id"])
                    name = system['name']
                    
                    if 'coords' in system:
                        coords = system['coords']
                        
                        if 'x' in coords:
                            x = coords['x']
                            y = coords['y']
                            z = coords['z']
                        else:
                            x = y = z = None
                    else:
                        x = y = z = None
                        
                    cursor.execute(sql, (_id, name, float(x), float(y), float(z)))

                self._dbconn.commit()
    
                return self.__get_utc(days = -1)
        except sqlite3.Error, e:
            self._log.error("Systems: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()
            
        return 0
    
    def __pull_distances(self, onprogress = None):
        cursor = None
        
        try:
            if onprogress:
                onprogress("Create EDSM Database - Downloading Distances Nightly...")
                
            cursor = self._dbconn.cursor()
             
            handle = urllib2.urlopen("http://www.edsm.net/dump/distances.json", timeout = 60)
            if handle:
                sql = "INSERT INTO %s (%s, %s, %s, %s) VALUES (?, ?, ?, ?)" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO, EDSMDistances.COLUMN_NAME_DISTANCE, EDSMDistances.COLUMN_NAME_DATE)

                count = 0
                for distance in ijson.items(handle, 'item'):
                    count = count + 1
                    if (count % 100) == 0:
                        if onprogress:
                            onprogress("Create EDSM Database - Processed [%d] Distances..." % count)

                    _from = distance['sys1']['name']
                    _to = distance['sys2']['name']
                    _dist = float(distance['distance'])

                    _date = self.__get_datetime(timestring = distance['date'])
                    _date = self.__get_utc(dt = _date)

                    cursor.execute(sql, (_from, _to, _dist, _date))
                    
                self._dbconn.commit()
                 
                return self.__get_utc(days = -1)
        except sqlite3.Error, e:
            self._log.error("Distances: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()
            
        return 0
        
    def __setup_info(self, last_check):
        cursor = None
        
        try:
            sql = "INSERT INTO %s (%s, %s) VALUES (?, ?);" % (DbInfo.TABLE_NAME, DbInfo.COLUMN_NAME_CONFIG, DbInfo.COLUMN_NAME_VALUE)
    
            cursor = self._dbconn.cursor()
            cursor.execute(sql, (DbInfo.CONFIG_NAME_LAST_EDSM_CHECK, str(last_check)))
    
            # Now everything is done so create all the indexes
            sql = "CREATE INDEX EDSMSystemIndex ON %s(%s);" % (EDSMSystems.TABLE_NAME, EDSMSystems.COLUMN_NAME_SYSTEM)
            cursor.execute(sql)
            sql = "CREATE INDEX EDSMSystemCoordIndex ON %s(%s,%s,%s);" % (EDSMSystems.TABLE_NAME, EDSMSystems.COLUMN_NAME_XCOORD, EDSMSystems.COLUMN_NAME_YCOORD, EDSMSystems.COLUMN_NAME_ZCOORD)
            cursor.execute(sql)
        
            sql = "CREATE INDEX EDSMDistIndex ON %s(%s, %s);" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM, EDSMDistances.COLUMN_NAME_TO)
            cursor.execute(sql)
            sql = "CREATE INDEX EDSMFromDistIndex ON %s(%s);" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_FROM)
            cursor.execute(sql)
            sql = "CREATE INDEX EDSMToDistIndex ON %s(%s);" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_TO)
            cursor.execute(sql)
            sql = "CREATE INDEX EDSMDistanceIndex ON %s(%s);" % (EDSMDistances.TABLE_NAME, EDSMDistances.COLUMN_NAME_DISTANCE)
            cursor.execute(sql)

            self._dbconn.commit()
        except sqlite3.Error, e:
            self._log.error("Setup: SQLite error %s:" % e.args[0])
        finally:
            if cursor:
                cursor.close()

_edsm_db = EDSMDb()
def get_instance():
    return _edsm_db

def _test_update_db():
    _t0 = datetime.datetime.utcnow()
    edsm_db = get_instance()
    edsm_db.update()
 
    print "Update time:", (datetime.datetime.utcnow() - _t0)
    
    edsm_db.close()
    
def _test_get_distances():
    edsm_db = EDSMDb()

    dist_list = edsm_db.get_distances('Sol')
    for item in dist_list:
        print item
    
    edsm_db.close()

def _test_get_distance():
    edsm_db = EDSMDb()

    print edsm_db.get_distance('Sol', 'Cephei Sector MN-T b3-0')
    
    edsm_db.close()
    
if __name__ == "__main__":
    user_dir = os.path.join(edutils.get_user_dir(), ".edproxy")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
 
    user_dir = os.path.join(user_dir, "edproxy.log")
    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir)

    _test_update_db()
#     _test_get_distances()
#     _test_get_distance()
