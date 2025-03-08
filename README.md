# Compiler

## Prerequisites

- `python3`

## Contents

- `lexer.py` - lexer
- `parser.py` - parser
- `generator.py` - source code to virtual machine's code generation proccess
- `compiler.py` - entry point
- `README.md` - name says everything :)

## Running

### Setup

It's a good practice to run python projects through venv

```
python -m venv .venv
```

```
source /.venv/bin/activate
```

```
pip install -r requirements.txt
```


### Source code compilation

```
python compiler.py <input_program> <out_compiled_program>
```


### Virtual machine execution

```
make ./maszyna-wirtualna/maszyna-wirtualna
```


```
./maszyna_wirtualna/maszyna-wirtualna  <out_compiled_program>

```


### Exit

Remember to deactivate venv:

```
deactivate
```