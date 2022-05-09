async function registro() {
    const respuesta = await fetch('/api/registro', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({a: 1, b: 'Textual content'})
    });
    const content = await respuesta.json();
  
    console.log(content);
  };