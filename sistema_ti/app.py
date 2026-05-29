from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "chave_secreta_para_alertas"

DB_PATH = "banco.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cpf TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL
    )
                   
''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Equipamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            numero_serie TEXT UNIQUE NOT NULL,
            data_acisicao TEXT NOT NULL,
            localizacao TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Registro_Suporte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_equipamento INTEGER NOT NULL,
            data_suporte TEXT NOT NULL,
            tipo_suporte TEXT NOT NULL,
            descricao TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            custo DECIMAL(10,2),
            FOREIGN KEY (id_equipamento) REFERENCES Equipamento(id)
        )
        
    ''')
    cursor.execute("SELECT * FROM Usuario WHERE cpf = ?", ("12345678900",))
    usuario = cursor.fetchone()

    if not usuario:
        cursor.execute('''
            INSERT INTO Usuario (nome, cpf, senha)
            VALUES (?, ?, ?)
        ''', ("Administrador", "12345678900", "123"))

    conn.commit()
    conn.close()
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        cpf = request.form['cpf']
        senha = request.form['senha']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM Usuario
            WHERE cpf = ? AND senha = ?
        ''', (cpf, senha))

        usuario = cursor.fetchone()

        conn.close()

        if usuario:
            session['usuario'] = usuario[1]
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('CPF ou senha inválidos.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Logout realizado com sucesso!', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastrar_usuario():

    if request.method == 'POST':

        nome = request.form['nome']
        cpf = request.form['cpf']
        senha = request.form['senha']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:

            cursor.execute('''
                INSERT INTO Usuario (nome, cpf, senha)
                VALUES (?, ?, ?)
            ''', (nome, cpf, senha))

            conn.commit()

            flash('Usuário cadastrado com sucesso!', 'success')

            return redirect(url_for('login'))

        except sqlite3.IntegrityError:

            flash('CPF já cadastrado no sistema.', 'danger')

        finally:

            conn.close()

    return render_template('cadastro_usuario.html')

@app.route('/')
def index():

    if 'usuario' not in session:
        return redirect(url_for('login'))

    tipo = request.args.get('tipo', '')
    status = request.args.get('status', '')
    localizacao = request.args.get('localizacao', '')
    marca = request.args.get('marca', '')
    busca = request.args.get('busca', '')

    query = "SELECT * FROM Equipamento WHERE 1=1"
    params = []

    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    if status:
        query += " AND status = ?"
        params.append(status)
    if localizacao:
        query += " AND localizacao LIKE ?"
        params.append(f"%{localizacao}%")
    if marca:
        query += " AND marca LIKE ?"
        params.append(f"%{marca}%")
    if busca:
        query += " AND (numero_serie = ? OR id = ? OR patrimonio = ?)"
        params.extend([busca, busca, busca])

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    equipamentos = cursor.fetchall()
    conn.close()

    return render_template(
        'index.html',
        equipamentos=equipamentos,
        filtros=request.args
    )

@app.route('/equipamento/novo', methods=['GET', 'POST'])
def cadastrar_equipamento():
    if request.method == 'POST':
        dados = (
            request.form['patrimonio'], request.form['tipo'], request.form['marca'],
            request.form['modelo'], request.form['numero_serie'], request.form['data_acisicao'],
            request.form['localizacao'], request.form['status']
        )
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Equipamento (patrimonio, tipo, marca, modelo, numero_serie, data_acisicao, localizacao, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', dados)
            conn.commit()
            flash("Equipamento cadastrado com sucesso!", "success")
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash("Erro: Patrimônio ou Número de Série já cadastrado.", "danger")
        finally:
            conn.close()
            
    return render_template('cadastrar_equipamento.html')

@app.route('/equipamento/editar/<int:id>', methods=['GET', 'POST'])
def editar_equipamento(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        cursor.execute('''
            UPDATE Equipamento SET 
            patrimonio=?, tipo=?, marca=?, modelo=?, numero_serie=?, data_acisicao=?, localizacao=?, status=?
            WHERE id=?
        ''', (
            request.form['patrimonio'], request.form['tipo'], request.form['marca'],
            request.form['modelo'], request.form['numero_serie'], request.form['data_acisicao'],
            request.form['localizacao'], request.form['status'], id
        ))
        conn.commit()
        conn.close()
        flash("Equipamento atualizado com sucesso!", "success")
        return redirect(url_for('index'))
        
    cursor.execute("SELECT * FROM Equipamento WHERE id = ?", (id,))
    equipamento = cursor.fetchone()
    conn.close()
    return render_template('cadastrar_equipamento.html', equipamento=equipamento)

@app.route('/equipamento/deletar/<int:id>')
def deletar_equipamento(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Registro_Suporte WHERE id_equipamento = ?", (id,))
    tem_suporte = cursor.fetchone()[0] > 0
    
    if tem_suporte:
        cursor.execute("UPDATE Equipamento SET status = 'Desativado' WHERE id = ?", (id,))
        flash("O equipamento possui históricos de suporte. Seu status foi alterado para 'Desativado'.", "warning")
    else:
        cursor.execute("DELETE FROM Equipamento WHERE id = ?", (id,))
        flash("Equipamento excluído com sucesso.", "success")
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/suporte/<int:id_equipamento>')
def registros_suporte(id_equipamento):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Equipamento WHERE id = ?", (id_equipamento,))
    equipamento = cursor.fetchone()
    
    cursor.execute("SELECT * FROM Registro_Suporte WHERE id_equipamento = ?", (id_equipamento,))
    suportes = cursor.fetchall()
    conn.close()
    return render_template('registros.html', equipamento=equipamento, suportes=suportes)

@app.route('/suporte/<int:id_equipamento>/novo', methods=['GET', 'POST'])
def novo_suporte(id_equipamento):
    if request.method == 'POST':
        custo = request.form['custo'] if request.form['custo'] else 0.0
        dados = (
            id_equipamento, request.form['data_suporte'], request.form['tipo_suporte'],
            request.form['descricao'], request.form['responsavel'], custo
        )
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Registro_Suporte (id_equipamento, data_suporte, tipo_suporte, descricao, responsavel, custo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', dados)
        conn.commit()
        conn.close()
        flash("Registro de suporte adicionado com sucesso!", "success")
        return redirect(url_for('registros_suporte', id_equipamento=id_equipamento))
        
    return render_template('novo_suporte.html', id_equipamento=id_equipamento)

@app.route('/suporte/deletar/<int:id>/<int:id_equipamento>')
def deletar_suporte(id, id_equipamento):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Registro_Suporte WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Registro excluído (Apenas permitido por erro de cadastro).", "info")
    return redirect(url_for('registros_suporte', id_equipamento=id_equipamento))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)