import os
import subprocess
import tempfile  # Add this import
from flask import Flask, render_template, request, jsonify
import uuid
import signal

app = Flask(__name__)

# Error handler to ensure JSON responses
@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON instead of HTML for API routes."""
    app.logger.error(f"Server error: {str(e)}")
    return jsonify({"output": f"Server error: {str(e)}"}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/c-to-assembly')
def c_to_assembly():
    return render_template('c-to-assembly.html')

@app.route('/c-compiler')
def c_compiler():
    return render_template('c-compiler.html')

@app.route('/assembly-compiler')
def assembly_compiler():
    return render_template('assembly-compiler.html')

@app.route('/compile-to-assembly', methods=['POST'])
def compile_to_assembly():
    try:
        data = request.json
        if not data:
            return jsonify({"assemblyCode": "Error: No data received"}), 400
            
        c_code = data.get('code', '')
        temp_id = uuid.uuid4().hex
        c_file = f"temp_{temp_id}.c"
        s_file = f"temp_{temp_id}.s"

        # Write C code to a temporary file
        with open(c_file, "w") as file:
            file.write(c_code)

        try:
            # Compile C code to assembly using GCC with optimizations disabled
            result = subprocess.run(
                ["gcc", "-S", "-fno-asynchronous-unwind-tables", "-o", s_file, c_file],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                with open(s_file, "r") as file:
                    assembly_code = file.read()
            else:
                assembly_code = f"Compilation Error:\n{result.stderr}"

        except subprocess.TimeoutExpired:
            assembly_code = "Compilation timed out (limit: 10 seconds)"
        except Exception as e:
            assembly_code = f"Error: {str(e)}"

        # Clean up temp files
        for f in [c_file, s_file]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass

        return jsonify({'assemblyCode': assembly_code})
    
    except Exception as e:
        app.logger.error(f"Error in compile-to-assembly: {str(e)}")
        return jsonify({"assemblyCode": f"Server error: {str(e)}"}), 500

@app.route('/compile-and-run-c', methods=['POST'])
def compile_and_run_c():
    data = request.json
    c_code = data.get('code', '')
    user_input = data.get('input', '')

    # Check if code contains input functions
    needs_input = any(keyword in c_code.lower() for keyword in ['scanf', 'getchar', 'gets', 'fgets'])
    
    # If this is the first check and input is needed
    if needs_input and not user_input:
        return jsonify({'needsInput': True})

    # Create a temporary file for the C code
    with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as f:
        f.write(c_code.encode())
        c_file = f.name

    # Create a temporary file for the executable
    exe_file = c_file[:-2] + '.exe'

    try:
        # Compile the C code
        compile_process = subprocess.run(['gcc', c_file, '-o', exe_file], 
                                        capture_output=True, text=True, check=False)
        
        if compile_process.returncode != 0:
            return jsonify({'output': f"Compilation Error:\n{compile_process.stderr}"})
        
        # Run the executable with a timeout
        # Fix: Use a list for the command arguments instead of a string
        cmd = [exe_file]
        
        # If user input is provided, prepare it
        if user_input:
            run_process = subprocess.run(cmd, input=user_input, 
                                        capture_output=True, text=True, timeout=5)
        else:
            run_process = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        output = run_process.stdout
        if run_process.stderr:
            output += f"\nStderr:\n{run_process.stderr}"
            
        return jsonify({'output': output})
    
    except subprocess.TimeoutExpired:
        return jsonify({'output': 'Execution timed out. Your program may have an infinite loop.'})
    except Exception as e:
        return jsonify({'output': f'Error: {str(e)}'})
    finally:
        # Clean up temporary files
        try:
            os.unlink(c_file)
            if os.path.exists(exe_file):
                os.unlink(exe_file)
        except:
            pass

@app.route('/compile-and-run-assembly', methods=['POST'])
def compile_and_run_assembly():
    try:
        data = request.json
        if not data:
            return jsonify({"output": "Error: No data received"}), 400
            
        asm_code = data.get('code', '')
        user_input = data.get('input', '')

        temp_id = uuid.uuid4().hex
        asm_file = f"temp_{temp_id}.s"
        # Use a more complete path for the executable
        exec_file = os.path.join(os.getcwd(), f"temp_{temp_id}")

        # Write Assembly code to a temporary file
        with open(asm_file, "w") as file:
            file.write(asm_code)

        output = ""
        try:
            # Compile and link the assembly file
            compile_process = subprocess.run(
                ["gcc", asm_file, "-o", exec_file],
                capture_output=True, text=True, timeout=10
            )
            
            if compile_process.returncode == 0:
                # Check if the executable was actually created
                if os.path.exists(exec_file):
                    # Run the compiled program
                    run_cmd = [exec_file]
                    
                    try:
                        run_process = subprocess.run(
                            run_cmd,
                            input=user_input,
                            capture_output=True, text=True, timeout=5
                        )
                        output = run_process.stdout
                        if run_process.returncode != 0:
                            output += f"\nProgram exited with status: {run_process.returncode}"
                        if run_process.stderr:
                            output += f"\nStderr:\n{run_process.stderr}"
                    except subprocess.TimeoutExpired:
                        output = "Execution timed out (limit: 5 seconds)"
                    except Exception as e:
                        output = f"Runtime Error: {str(e)}"
                else:
                    output = f"Error: Executable file was not created after successful compilation."
            else:
                output = f"Assembly/Linking Error:\n{compile_process.stderr}"
                
        except subprocess.TimeoutExpired:
            output = "Compilation timed out (limit: 10 seconds)"
        except Exception as e:
            output = f"Error: {str(e)}"

        # Clean up temp files
        for f in [asm_file, exec_file]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                app.logger.error(f"Error removing temp file {f}: {str(e)}")

        return jsonify({'output': output})
    
    except Exception as e:
        app.logger.error(f"Error in compile-and-run-assembly: {str(e)}")
        return jsonify({"output": f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)