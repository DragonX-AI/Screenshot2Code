import os
import shutil
import sys
from typing import Tuple, Union

import pandas as pd
import pytesseract as tess
from guesslang import Guess
from PIL import Image
from pytesseract import Output

log_file = open("log", "w")


class Screenshot2Code:
    @staticmethod
    def version_check():
        print("Python version: ", sys.version)
        if sys.version_info < (3, 9):
            raise Exception("This program requires at least Python 3.9")

    @staticmethod
    def copy_to_clipboard(filename: Union[str, None]):
        # maybe something went wrong?
        if filename is None:
            raise Exception(f"filename `{filename}` argument is empty")
        if not os.path.isfile(filename):
            raise Exception(f"`{filename}` is not a file")

        print("Copying to clipboard...")
        # TODO: use filename instead of text value for Win32 and MacOS
        if sys.platform == "win32":
            # Windows
            command = "echo " + filename.strip() + "| clip"
            os.system(command)
        elif sys.platform == "darwin":
            # macOS
            command = "echo " + filename.strip() + "| pbcopy"
            os.system(command)
        else:
            # Linux and other Unix-based systems
            if not shutil.which("xsel"):
                raise Exception("You do not have `xsel` installed.")

            command = "xsel --clipboard <" + filename
            os.system(command)

    # Set the path to the Tesseract OCR executable
    @staticmethod
    def check_for_tesseract():
        tess_cmd = shutil.which("tesseract")
        if tess_cmd is None:
            raise Exception("Please make sure you have tesseract installed")
        tess.pytesseract.tesseract_cmd = tess_cmd
        return True

    # FIXME: enforce dealing with the TESSDATA_PREFIX prefix
    @staticmethod
    def check_for_tessdata_prefix() -> bool:
        if os.environ.get("TESSDATA_PREFIX"):
            print("log: TESSDATA_PREFIX has been defined", file=sys.stderr)
        else:
            # not sure how to deal with this yet
            os.environ["TESSDATA_PREFIX"] = "./tess_data_bak"
        return True

    # FIXME: sometime the space formatting is very wrong
    @staticmethod
    def preserve_identation(frame: pd.DataFrame) -> str:
        df1 = frame[(frame.conf != "-1") & (frame.text != " ") & (frame.text != "")]

        # sort blocks vertically
        code = ""
        sorted_blocks = (
            df1.groupby("block_num").first().sort_values("top").index.tolist()
        )
        for block in sorted_blocks:
            curr = df1[df1["block_num"] == block]
            sel = curr[curr.text.str.len() > 3]
            char_w = (sel.width / sel.text.str.len()).mean()
            prev_par, prev_line, prev_left = 0, 0, 0
            text = ""
            for ix, ln in curr.iterrows():
                # add new line when necessary
                if prev_par != ln["par_num"]:
                    text += "\n"
                    prev_par = ln["par_num"]
                    prev_line = ln["line_num"]
                    prev_left = 0
                elif prev_line != ln["line_num"]:
                    text += "\n"
                    prev_line = ln["line_num"]
                    prev_left = 0

                added = 0  # num of spaces that should be added
                if ln["left"] / char_w > prev_left + 1:
                    added = int((ln["left"]) / char_w) - prev_left
                    text += " " * 2 * added  # go extra on identation by default
                text += ln["text"] + " "
                prev_left += len(ln["text"]) + added + 1
            text += "\n"
            code += text

        return code

    @staticmethod
    def guess_lang(text_in: str) -> Union[str, None]:
        print(text_in, file=log_file)
        guess = Guess()
        name = guess.language_name(text_in)
        print(f"The language guessed is {name}", file=log_file)
        return name

    @staticmethod
    def lang_to_extension(lang: str) -> Union[str, None]:
        lang_extensions = {
            "Assembly": ".asm",
            "Batchfile": ".bat",
            "C": ".c",
            "C#": ".cs",
            "C++": ".cpp",
            "Clojure": ".clj",
            "CMake": ".cmake",
            "COBOL": ".cbl",
            "CoffeeScript": ".coffee",
            "CSS": ".css",
            "CSV": ".csv",
            "Dart": ".dart",
            "DM": ".dm",
            "Dockerfile": ".dockerfile",
            "Elixir": ".ex",
            "Erlang": ".erl",
            "Fortran": ".f",
            "Go": ".go",
            "Groovy": ".groovy",
            "Haskell": ".hs",
            "HTML": ".html",
            "INI": ".ini",
            "Java": ".java",
            "JavaScript": ".js",
            "JSON": ".json",
            "Julia": ".jl",
            "Kotlin": ".kt",
            "Lisp": ".lisp",
            "Lua": ".lua",
            "Makefile": ".mk",
            "Markdown": ".md",
            "Matlab": ".m",
            "Objective-C": ".m",
            "OCaml": ".ml",
            "Pascal": ".pas",
            "Perl": ".pl",
            "PHP": ".php",
            "PowerShell": ".ps1",
            "Prolog": ".pl",
            "Python": ".py",
            "R": ".R",
            "Ruby": ".rb",
            "Rust": ".rs",
            "Scala": ".scala",
            "Shell": ".sh",
            "SQL": ".sql",
            "Swift": ".swift",
            "TeX": ".tex",
            "TOML": ".toml",
            "TypeScript": ".ts",
            "Verilog": ".v",
            "Visual Basic": ".vb",
            "XML": ".xml",
            "YAML": ".yml",
        }

        return lang_extensions.get(lang, None)

    def convert(self, image_path: str) -> Tuple[Union[str, None], Union[str, None]]:
        try:
            img = Image.open(image_path)

            # Custom Tesseract configuration for preserving whitespace and formatting
            config = r"-c preserve_interword_spaces=1 --psm 6 --oem 3"

            text_data = tess.image_to_data(img, config=config, output_type=Output.DICT)
            frame = pd.DataFrame(text_data)
            text = self.preserve_identation(frame)

            lang = self.guess_lang(text)

            return lang, text

        except Exception as e:
            print("Error:", str(e), file=log_file)
            return None, None


if __name__ == "__main__":
    S2C = Screenshot2Code()
    S2C.version_check()
    if S2C.check_for_tesseract() is False:
        print("Please make sure you have tesseract installed.", file=sys.stderr)
        exit(1)
    S2C.check_for_tessdata_prefix()

    if len(sys.argv) == 3:
        image_path = sys.argv[1]
        output_path = sys.argv[2]

        lang, text = S2C.convert(image_path)
        with open(output_path, "w") as f:
            if text:
                f.write(text)
        S2C.copy_to_clipboard(output_path)
    else:
        print("Usage: python screenshot2code.py <screenshot_path> <output_path>")
