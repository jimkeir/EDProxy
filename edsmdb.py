import datetime
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
import math
import time
import lru
import wx

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
        
        if row[2] != None and row[3] != None and row[4] != None:
            self.position = (row[2], row[3], row[4])
        else:
            self.position = None
        
    def __str__(self, *args, **kwargs):
        return "EDSMSystems [id: %d, name: %s, coord: %s]" % (self.id, self.name, str(self.position))

class EDSMDistance(object):
    def __init__(self, sys1, sys2, distance):
        self.sys1 = sys1
        self.sys2 = sys2
        self.distance = distance
        
    def __str__(self, *args, **kwargs):
        return "EDSMDistance [sys1: %s, sys2: %s, distance: %.2f]" % (self.sys1, self.sys2, self.distance)

    def __eq__(self, other):
        if not isinstance(other, EDSMDistance):
            return False
        
        return self.sys1.name == other.sys1.name and self.sys2.name == other.sys2.name
    
    def __ne__(self, other):
        if not isinstance(other, EDSMDistance):
            return True
        
        return self.sys1.name != other.sys1.name or self.sys2.name != other.sys2.name
    
    def __hash__(self):
        return hash("%s:%s" % (self.sys1.name, self.sys2.name))
    
class EDSMDb(object):
    def __init__(self):
        self._log = logging.getLogger("com.fussyware.edproxy")
        
        self._db_version = 1

        edproxy_db_dir = edutils.get_database_dir()
        self._edproxy_db_filename = os.path.join(edproxy_db_dir, "edsm.db")
        
        self._first_time_install = False
        self._dbconn = None
        
        self._update_event = threading.Event()
        self._background_update_running = False
        
        self._lru = lru.LRU(max_size = 25)
        
        if (not os.path.exists(edproxy_db_dir)):
            os.makedirs(edproxy_db_dir)
            
        if (not os.path.exists(self._edproxy_db_filename)):
            self.__do_create_db(self._edproxy_db_filename)
        else:
            self._dbconn = sqlite3.connect(self._edproxy_db_filename, check_same_thread=False)
            
        self.__db_upgrade(self.__get_db_version())
        self._dbconn.close()
        self._dbconn = None

    def is_connected(self):
        return (self._dbconn != None)
    
    def connect(self):
        if not self._dbconn:
            if (not os.path.exists(self._edproxy_db_filename)):
                self.__do_create_db(self._edproxy_db_filename)

            self._dbconn = sqlite3.connect(self._edproxy_db_filename, check_same_thread=False)
       
    def erase(self):
        self.close()
        os.remove(self._edproxy_db_filename)

    def close(self):
        self.stop_background_update()
        
        if self._dbconn:
            self._dbconn.close()
            self._dbconn = None
        
    def is_install_required(self):
        return self._first_time_install
    
    def install_edsmdb(self, onprogress = None):
        if self._first_time_install:
            # Go back in time by a day so that we absolutely do not miss anything
            # from when the database was first created.
            last_check = self.__get_utc(days = -1)
            
            self.__pull_systems(onprogress)
            self.__setup_info(last_check)
                    
            self._first_time_install = False
    
    def start_background_update(self, onupdate = None):
        if self._background_update_running:
            return

        self._update_event.clear()
        self._background_update_running = True
        
        _thread = threading.Thread(target = self.__background_updater, args = (onupdate,))
        _thread.daemon = True
        _thread.start()

    def stop_background_update(self):
        if not self._background_update_running:
            return

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
            return None
        finally:
            if cursor:
                cursor.close()

    def get_distances(self, system, radius):
        dist_list = self._lru.get(system)
        
        if not dist_list:
            dist_list = set()
        
            system = self.get_system(system)
            
            if system and system.position:
                xcoord_query = "xCoord BETWEEN %f AND %f AND" % (system.position[0] - radius,
                                                                 system.position[0] + radius)
                ycoord_query = "yCoord BETWEEN %f AND %f AND" % (system.position[1] - radius,
                                                                 system.position[1] + radius)
                zcoord_query = "zCoord BETWEEN %f AND %f" % (system.position[2] - radius,
                                                             system.position[2] + radius)
            
                query = "SELECT * FROM %s WHERE %s %s %s" % (EDSMSystems.TABLE_NAME, xcoord_query, ycoord_query, zcoord_query)
    
                cursor = None
                try:
                    cursor = self._dbconn.cursor()
                    cursor_list = cursor.execute(query).fetchall()
                    
                    radius_squared = math.pow(radius, 2)
                    
                    for row in cursor_list:
                        row_system = EDSMSystem(row)
                        if row_system.name != system.name and row_system.position:
                            distance = self.__get_squared_distance(system.position, row_system.position)
                            if distance <= radius_squared:
                                distance = round(math.sqrt(distance), 2)
                                dist_list.add(EDSMDistance(system, row_system, distance))
                except sqlite3.Error:
                    self._log.exception("EDSM get distances: SQLite error")
                finally:
                    if cursor:
                        cursor.close()
                        
                dist_list = self._lru.put(system.name, sorted(dist_list, key=lambda distance: distance.distance))
        
        return dist_list
        

    def get_distance(self, sys1, sys2):
        _system1 = self.get_system(sys1)
        _system2 = self.get_system(sys2)
        
        if _system1 and _system1.position and _system2 and _system2.position:
            distance = math.sqrt(self.__get_squared_distance(_system1.position, _system2.position))
            distance = round(distance, 2)

            return EDSMDistance(_system1, _system2, distance)
        else:
            return None
                
    def __get_squared_distance(self, v0, v1):
        x = v1[0] - v0[0]
        y = v1[1] - v0[1]
        z = v1[2] - v0[2]
        
        return math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2)
        
    def __get_db_version(self):
        cursor = None
        
        try:
            cursor = self._dbconn.cursor()
            cursor.execute("PRAGMA user_version")
            return cursor.fetchone()[0]
        except:
            self._log.error("Error fetching EDSM database version number.")
        finally:
            if cursor:
                cursor.close()

    def __db_upgrade(self, db_version):
        cursor = None
        
        try:
            cursor = self._dbconn.cursor()

            if db_version == 0:
                self._log.info("Upgrading EDSM database from version 0 to version 1")
                
                db_version = 1
                
                cursor.execute("DROP INDEX IF EXISTS EDSMDistIndex")
                cursor.execute("DROP TABLE IF EXISTS %s" % EDSMDistances.TABLE_NAME)
                cursor.execute("PRAGMA user_version=%d" % db_version)

            self._dbconn.commit()
        except:
            self._log.exception("Error upgrading the database!")
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
            if self.__update_edsm() and onupdate:
                onupdate()
                
            self._update_event.wait(timeout = (5 * 60))
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
                            try:
                                cursor.execute(insert_sql, (_id, name, x, y, z))
                            except sqlite3.IntegrityError:
                                pass

                            updated = True
                        
                        if (count % 100000) == 0:
                            self._dbconn.commit()

                    self._dbconn.commit()
                    self._log.info("Updated [%d] systems" % (count))

                start_time = end_time
                end_time = start_time + datetime.timedelta(days = 14)
                end_time = min(end_time, now)
                
                self.__update_last_check(cursor, self.__get_utc(dt = start_time))
        except sqlite3.Error, e:
            self._log.error("EDSM Update: SQLite error %s:" % e.args[0])
        except:
            self._log.exception("Failed updating EDSM Database for unknown reason")
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
        
            sql = "CREATE TABLE %s (%s INTEGER PRIMARY KEY, %s TEXT, %s TEXT)" % (DbInfo.TABLE_NAME, DbInfo.ID, DbInfo.COLUMN_NAME_CONFIG, DbInfo.COLUMN_NAME_VALUE)
            cursor.execute(sql)

            cursor.execute("PRAGMA user_version=%d" % self._db_version)

            self._dbconn.commit()
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
                            if not onprogress("Create EDSM Database - Processed [%d] Systems..." % count):
                                break
                        
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

                    try:
                        cursor.execute(sql,
                                       (_id, name, float(x), float(y), float(z)))
                    except sqlite3.IntegrityError:
                        pass

                    if (count % 100000) == 0:
                        self._dbconn.commit()
                    
                self._dbconn.commit()

                cursor.execute("ANALYZE")

                self._log.info("Initialzed EDSM Database with [%d] systems." % count)
                
                return self.__get_utc(days = -1)
        except sqlite3.Error, e:
            self._log.error("Systems: SQLite error %s:" % e.args[0])
        except Exception, e:
            self._log.error("Systems: EDSM download error %s:" % e.message)

            if onprogress:
                onprogress("Error getting EDSM nightly database: " + e.message, True)
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
    edsm_db.connect()
    edsm_db.update()
 
    print "Update time:", (datetime.datetime.utcnow() - _t0)
    
    edsm_db.close()
    
def _test_get_distances():
    edsm_db = get_instance()
    edsm_db.connect()

    import cProfile, pstats, StringIO
    pr = cProfile.Profile()
    pr.enable()

#     t0 = time.time()
    dist_list = edsm_db.get_distances('Sol', 120.0)
#     t1 = time.time() - t0

    pr.disable()
    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    print s.getvalue()
    
#     for item in dist_list:
#     for i in xrange(0, 25):
#         print i, dist_list[i]
#     
#     print "time: ", t1
#     print "size: ", len(dist_list)
    edsm_db.close()

def _test_get_distance():
    edsm_db = get_instance()
    edsm_db.connect()

    print edsm_db.get_distance('Sol', 'Cephei Sector MN-T b3-0')
    
    edsm_db.close()
    
if __name__ == "__main__":
    user_dir = os.path.join(edutils.get_user_dir(), ".edproxy")
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
 
    user_dir = os.path.join(user_dir, "edproxy.log")
    logging.basicConfig(format = "%(asctime)s-%(levelname)s-%(filename)s-%(lineno)d    %(message)s", filename = user_dir)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

#    _test_update_db()
    _test_get_distances()
#     _test_get_distance()
