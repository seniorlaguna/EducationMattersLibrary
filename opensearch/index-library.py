import os
import logging
from os.path import exists, join, isdir, isfile
import json
import requests
import tika
from tika import parser

class Material:
    loggingEnabled: bool = False

    @staticmethod
    def enableLogging(flag: bool):
        Material.loggingEnabled = flag

    def __init__(self, id: str, enableLogging = True):
        self.id = id
        self.info = None

        if self.__checkPrerequisites():
            self.__populateInfoJson()
            self.__addThumbnails()

    def __checkPrerequisites(self) -> bool:
        self.__log("Checking material " + self.id, logging.DEBUG)        
        if not self.__checkInfoJson():
            return False
        if not exists(f"{self.id}/thumbnails") or not isdir(f"{self.id}/thumbnails"):
            self.__log("doesn't contain a thumbnails directory")
            return False

        return True

    def __checkInfoJson(self) -> bool:
        path = join(self.id, "info.json")
        if not exists(path) or not isfile(path):
            self.__log(f"info.json doesnt exist for material {self.id}", level=logging.ERROR)
            return False
        
        info = None
        with open(path, "r") as file:
            text = file.read()
            info = json.loads(text)
        
        if info is None:
            self.__log(f"Couldnt open info.json", logging.ERROR)
            return False

        if not self.__checkInfoJsonType(info):
            return False
        
        if not self.__checkInfoJsonFields(info):
            return False
        
        self.info = info
        return True

    def __checkInfoJsonType(self, info) -> bool:
        """
        Checks if the info.json file is a dictonary
        """
        if type(info) is not dict:
            self.__log(f"material {self.id} has a invalid info.json: {info}", logging.ERROR)
            return False
        
        return True

    def __checkInfoJsonFields(self, info: dict) -> bool:
        """
        Checks if all required fields are in the info.json
        """

        # Requirements (key, type, optional check, error message for check)
        requirements = [
            ("name", str, lambda x: len(x) > 0, "Material name must not be empty"),
            ("description", str, lambda x: len(x) > 0, "Description must not be empty"),
            ("subjects", list, lambda x: all(type(i) == str and len(i) > 0 for i in x), "All subjects must be of type string and must not be empty"),
            ("grades", list, lambda x: all(type(i) == int for i in x), "All grades must be of type int"),
            ("tags", list, lambda x: all(type(i) == str and len(i) > 0 for i in x), "All tags must be of type string and must not be empty"),
            ("type", str, lambda x: len(x) > 0, "Type must not be empty"),
            ("persons", list, lambda x: True, ""),
            ("file", str, lambda x: len(x) > 0, "File must not be empty")
        ]

        for (k, t, c, m) in requirements:
            try:
                value = info[k]
                if (type(value) is not t):
                    raise ValueError(f"Material type must be {t}")
                if (not c(value)):
                    raise ValueError(m)
            except KeyError as e:
                self.__log(f"info.json must contain the field: {e}", logging.ERROR)
                return False
            except ValueError as e:
                self.__log(str(e), logging.ERROR)
                return False
        
        return True

    def __populateInfoJson(self):
        self.info["name_completion"] = self.info["name"]

        try:
            parsed = parser.from_file(join(self.id, self.info["file"]))
            text = " ".join(parsed["content"].split())

            self.info["text_content"] = text
        except:
            self.info["text_content"] = ""

    def __addThumbnails(self):
        self.info["thumbnails"] = []
        for file in os.scandir(f"{self.id}/thumbnails"):
            if file.is_file():
                self.info["thumbnails"].append(file.name)

    def __log(self, msg, level=logging.INFO):
        if Material.loggingEnabled:
            logging.log(level, f"[Material {self.id}] {msg}")

    def __str__(self):
        if self.info is None:
            return ""

        return f'{{ "index": {{ "_index": "materials", "_id": {self.id} }} }}\n' + \
               json.dumps(self.info) + "\n"

def main():
    tika.initVM()

    materials: list[Material] = []
    for entry in os.scandir("./"):
        if entry.is_dir() and entry.name.isnumeric():
            materials.append(Material(entry.name))

    data = ""
    correctMaterials = 0
 
    for material in materials:
        if material.info is not None:
            correctMaterials += 1
            data += str(material)

    print(os.environ["OPENSEARCH"])
    print(data)
    return

    headers = {"Content-Type": "application/x-ndjson"}
    resp = requests.put("https://localhost:9200/materials/_bulk", headers=headers, auth=("admin", "admin"), verify=False, data=data)

    
    logging.info("[*] REPORT")
    logging.info(f"[*] {correctMaterials} / {len(materials)} materials are valid")
    if resp.status_code == 200:
        logging.info("[*] updated index successfully")
    else:
        logging.error(f"[!] update failed: {resp.text}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Material.enableLogging(True)
    main()