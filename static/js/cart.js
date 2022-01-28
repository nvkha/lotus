var updateBtns = document.getElementsByClassName('update-cart')

for(var i = 0; i < updateBtns.length; i++) {
    updateBtns[i].addEventListener('click', function(){
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('productId: ', productId, 'quantity:', quantity , 'action: ', action)

        console.log('User: ', user)
        if(user == '') {
            addCookieItem(productId, action, quantity)
        } else {
            updateUserOrder(productId, action, quantity)
        }
    })
}

function addCookieItem(productId, action, quantity) {
    console.log('Not logged in...')
    if (action == 'add') {
        if (cart[productId] == undefined) {
            cart[productId] = {'quantity': 1}
        }
        else {
            cart[productId]["quantity"] += 1
        }
    }

    if (action == 'remove') {
        cart[productId]["quantity"] -= 1

        if (cart[productId]["quantity"] <= 0) {
            console.log("Remove Item")
            delete cart[productId]
        }
    }

        if (action == 'delete') {
            console.log("Remove Item")
            delete cart[productId]
    }

    if (action == 'update') {
        if (cart[productId] == undefined) {
            cart[productId] = {'quantity': parseInt(quantity)}
        }
        else {
            cart[productId]["quantity"] += parseInt(quantity)
        }
    }
    document.cookie = 'cart=' + JSON.stringify(cart) + ';domain=;path=/'
    console.log('Cart:', cart)
    location.reload();
    
}

function updateUserOrder(productId, action, quantity) {
    console.log('User logged in, sending data')

    var url = "/update-item"
    fetch(url, {
        method: "POST",
        headers:{
            'Content-Type': 'application/json'
        },
        body:JSON.stringify({'productId': productId,'quantity':quantity ,'action':action})
    })
    .then((response) =>{
        return response.json()
    })

    .then((data) =>{
        console.log("data: ", data)
        location.reload()
    })
}