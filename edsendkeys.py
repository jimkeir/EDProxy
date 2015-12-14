import sys

if sys.platform == "win32":
    import SendKeys

def sendkeys(keys):
    if sys.platform == "win32":
        keys = keys.encode('ascii')
        
        # These are the preset keys within SendKeys
        keys = keys.replace('+', '{+}') \
                   .replace('^', '{^}') \
                   .replace('%', '{%}')
                   
        # Perform "shift" operations on all special characters
        keys = keys.replace('~', '+`') \
                   .replace('!', '+1') \
                   .replace('@', '+2') \
                   .replace('#', '+3') \
                   .replace('*', '+8') \
                   .replace('(', '+9') \
                   .replace(')', '+0') \
                   .replace('_', '-')
                   
        try:
            keys = """+{HOME}{BS}%s{ENTER}""" % keys
            SendKeys.SendKeys(keys = keys, pause = 0.02, with_spaces = True)
        except Exception, e:
            print e
