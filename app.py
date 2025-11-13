from flask import Flask, render_template

app = Flask(__name__, static_folder='assets', template_folder='webpages')

@app.route('/')
def product_page():
    return render_template('product_view.html')

if __name__ == '__main__':
    app.run(debug=True)
