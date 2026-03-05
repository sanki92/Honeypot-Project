import json
import re
import sys
import time
import logging
from typing import Tuple, List, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LineParser:
    '''parses audit_log.messages and audit_log.error_messages'''
    __tagRegex__ = ' \[.*? .*?\]|^\[.*? .*?\]'

    def __parseTag__(self, tag) -> Tuple[str, str]:
        tag = tag.strip()       
        tag = tag[1:-1]         
        tag = tag.split(" ", 1) 
        key = tag[0]
        value = tag[1][1:-1] if tag[1].startswith("\"") else tag[1] 
        return (key, value)

    def __parseMessages__(self, messages) -> Dict[str, Any]:
        events = dict()
        index = 0
        for message in messages:
            event = dict()
            
            tags = re.findall(self.__tagRegex__, message)
            for chunk in tags:
                [key, value] = self.__parseTag__(chunk)
                if (key == "tag"):
                    if (event.get('tags', None) == None):
                        event['tags'] = []
                    event['tags'].append(value)
                    pass
                else:
                    event[key] = value 
                    pass

            
            leftovers = (re.sub(self.__tagRegex__, '', message))
            leftovers = leftovers.split(".")

            event['type'] = leftovers[0].strip()
            event['pattern'] = leftovers[1].strip()
            events['message-' + str(index)] = event 
            index+= 1
        return events

    def parse(self, logLine) -> Dict[str, Any]:
        parsed = json.loads(logLine)
        parsed['messages'] = self.__parseMessages__(parsed['audit_data']['messages'])
        parsed['error_messages'] = self.__parseMessages__(parsed['audit_data']['error_messages'])
        del parsed['audit_data']['messages']
        del parsed['audit_data']['error_messages']
        return parsed

class fileHandler(FileSystemEventHandler):
    parser = LineParser()
    lineNum = None
    processdLineNum = None
    originalPath = "/var/log/modsec_audit.log"
    processedPath = "/var/log/modsec_audit_processed.log"
    
    def on_modified(self, event):
        if "modsec_audit.log" in event.src_path:
            log.info("Logfile changed")
            self.processLog()
        else:
            pass

    def processLog(self) -> None:
        
        processedLines = self.getLines(self.processedPath)
        lines = self.getLines(self.originalPath)
        procIndex = 0 if processedLines is None else len(processedLines)
        log.debug("Processed file lines", procIndex)
        origIndex = 0 if lines is None else len(lines)
        log.debug("Original file lines", origIndex)

        
        [index, writeMode] = self.getHead(origIndex, procIndex)
        log.debug("Head", index)
        log.debug("Write Mode", writeMode)

        
        newLines = []
        for i in range(index, len(lines)):
            newLines.append(json.dumps(self.parser.parse(lines[i])))

        
        try:
            file = open(self.processedPath, writeMode)
            for line in newLines:
                file.write(line + "\n")
            file.close()
        except Exception as e:
            log.error("Error writing to file", e)
    
    def getLines(self, path) -> List[str]:
        try:
            file = open(path, "r")
            lines = file.readlines()
            file.close()
            return lines
        except FileNotFoundError as e:
            return None

    def getHead(self, origFileIndex, newFileIndex) -> Tuple[int, str]:
        
        if (origFileIndex <= newFileIndex): return (0, "w")
        if (newFileIndex == 0): return (0, "a")
        if (newFileIndex > 0 and origFileIndex > newFileIndex): return (newFileIndex, "a")
        raise NotImplementedError("Case not implemented")
        
if __name__ == "__main__":
    PATH="/var/log/"
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
    log = logging.getLogger("Python-Script")
    handler = logging.FileHandler('/var/log/preprocess-script.log')
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    log.addHandler(handler)
    log.info("Python script is starting up...")
    event_handler = fileHandler()
    observer = Observer()
    observer.schedule(event_handler, PATH, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
