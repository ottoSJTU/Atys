import argparse
import os

def merge_collapsed(in_dir=str, out_path=str):
    with open(out_path, "a") as fo:
        for root, ds, fs in os.walk(in_dir):
            for f in fs:
                in_name = os.path.join(root, f)
                with open(in_name, "r") as fi:
                    fo.write(fi.read())
        os.removedirs(in_dir)
    return

def gen_flamegraph(fin, fout):
    os.system(f"java -cp ./utils/flamegraph/converter.jar FlameGraph {fin} {fout}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("in_dir")
    parser.add_argument("out_dir")
    args = parser.parse_args()
    
    out_collapsed = os.path.join(args.out_dir, "out_collapsed")
    out_flamegraph = os.path.join(args.out_dir, "out_flamegraph.html")
    
    merge_collapsed(args.in_dir, out_collapsed)
    gen_flamegraph(out_collapsed, out_flamegraph)
    os.remove(out_collapsed)
    
    
