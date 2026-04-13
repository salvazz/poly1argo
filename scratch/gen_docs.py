import os

def generate_consolidated_doc():
    files = [
        'Argo_Motor_24x7.py', 
        'Argo_Dashboard_Autonomo.py', 
        'bayesian_engine.py', 
        'Argo_Watchdog.py',
        'requirements.txt',
        '.env.example'
    ]
    
    header = """# ARGO V3 - ARCHIVO MAESTRO DE CONOCIMIENTO
Este documento consolida todo el sistema de trading autónomo Argo V3. 
Contiene el motor de ejecución, el dashboard premium, el motor bayesiano y el vigilante de Telegram.
Ideal para alimentar NotebookLM y obtener un análisis profundo del sistema.

---
"""
    
    doc_content = [header]
    
    for filename in files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    doc_content.append(f"## ARCHIVO: {filename}")
                    doc_content.append("```python" if filename.endswith('.py') else "```text")
                    doc_content.append(content)
                    doc_content.append("```\n")
                    doc_content.append("---\n")
            except Exception as e:
                doc_content.append(f"Error leyendo {filename}: {e}")
                
    final_output = "\n".join(doc_content)
    
    output_path = os.path.join('docs', 'ARGO_V3_CONSOLIDATED.md')
    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write(final_output)
    
    print(f"Documentación consolidada generada en: {output_path}")

if __name__ == "__main__":
    generate_consolidated_doc()
