from translate_cibd22x_to_v6 import translate_cibd22x_to_v6
import sys, json
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python translate_xml_cli.py <input.xml> [output.em_v6.json]")
        raise SystemExit(2)
    out = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1].rsplit('.',1)[0] + ".em_v6.json"
    em = translate_cibd22x_to_v6(sys.argv[1])
    json.dump(em, open(out,"w",encoding="utf-8"), indent=2)
    print("Wrote", out)
