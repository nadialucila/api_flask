async function redirigirRegistro() {
    const rawResponse = await fetch('/api/registro', {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      //body: JSON.stringify({a: 1, b: 'Textual content'})
    });
  };

 function fetchtest() {
    fetch('/api/registro').then(response => {
        return response
    })
 }
