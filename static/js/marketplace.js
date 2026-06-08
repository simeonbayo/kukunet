// static/js/marketplace.js

$(document).ready(function() {
    let currentPage = 1;
    let currentFilters = {
        category: '',
        product_type: '',
        min_price: '',
        max_price: '',
        ordering: '-created_at'
    };
    
    // Load products on page load
    loadProducts();
    loadCategories();
    loadCart();
    
    // Apply filters
    $('#applyFilters').click(function() {
        currentFilters = {
            category: $('#categoryFilter').val(),
            product_type: $('#typeFilter').val(),
            min_price: $('#minPrice').val(),
            max_price: $('#maxPrice').val(),
            ordering: $('#sortBy').val()
        };
        currentPage = 1;
        loadProducts();
    });
    
    // Load products with filters
    function loadProducts() {
        $('#productsGrid').html('<div class="col-span-full text-center py-12"><div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div><p class="mt-4 text-gray-600">Loading products...</p></div>');
        
        let params = {};
        if (currentFilters.product_type) params.product_type = currentFilters.product_type;
        if (currentFilters.min_price) params.min_price = currentFilters.min_price;
        if (currentFilters.max_price) params.max_price = currentFilters.max_price;
        if (currentFilters.ordering) params.ordering = currentFilters.ordering;
        if (currentPage > 1) params.page = currentPage;
        
        $.ajax({
            url: '/api/v1/products/',
            method: 'GET',
            data: params,
            success: function(response) {
                // Handle paginated response
                let products = response.results || response;
                let pagination = response;
                displayProducts(products);
                displayPagination(pagination);
            },
            error: function(xhr) {
                console.error('Error loading products:', xhr);
                showToast('Error loading products', 'error');
                $('#productsGrid').html('<div class="col-span-full text-center py-12 text-red-600">Failed to load products. Please try again.</div>');
            }
        });
    }
    
    // Display products grid
    function displayProducts(products) {
        if (!products || products.length === 0) {
            $('#productsGrid').html('<div class="col-span-full text-center py-12 text-gray-600">No products found</div>');
            return;
        }
        
        let html = '';
        products.forEach(product => {
            let stockClass = product.stock_quantity > 0 ? 'text-green-600' : 'text-red-600';
            let stockText = product.stock_quantity > 0 ? `In Stock (${product.stock_quantity})` : 'Out of Stock';
            let imageUrl = product.main_image || '/static/images/placeholder.png';
            
            html += `
                <div class="product-card bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition">
                    <img src="${imageUrl}" alt="${escapeHtml(product.name)}" class="w-full h-48 object-cover" onerror="this.src='/static/images/placeholder.png'">
                    <div class="p-4">
                        <h3 class="font-semibold text-lg text-gray-800 mb-2">${escapeHtml(product.name)}</h3>
                        <p class="text-gray-600 text-sm mb-2">${escapeHtml(product.short_description || (product.description ? product.description.substring(0, 80) : ''))}</p>
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-2xl font-bold text-green-600">UGX ${formatNumber(product.price)}</span>
                            ${product.compare_price ? `<span class="text-gray-400 line-through">UGX ${formatNumber(product.compare_price)}</span>` : ''}
                        </div>
                        <div class="mb-3">
                            <span class="${stockClass} text-sm">${stockText}</span>
                        </div>
                        <button onclick="addToCart(${product.id})" ${product.stock_quantity <= 0 ? 'disabled' : ''} 
                            class="w-full ${product.stock_quantity > 0 ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-400 cursor-not-allowed'} text-white py-2 rounded-lg transition">
                            Add to Cart
                        </button>
                    </div>
                </div>
            `;
        });
        $('#productsGrid').html(html);
    }
    
    // Load categories for filter
    function loadCategories() {
        $.ajax({
            url: '/api/v1/products/',
            method: 'GET',
            success: function(response) {
                let products = response.results || response;
                let categories = new Set();
                if (Array.isArray(products)) {
                    products.forEach(product => {
                        if (product.product_type) {
                            categories.add(product.product_type);
                        }
                    });
                }
                
                let options = '<option value="">All Categories</option>';
                const categoryNames = {
                    'DAY_OLD_CHICKS': 'Day Old Chicks',
                    'FEED': 'Feed',
                    'GLUCOSE': 'Glucose',
                    'MEDICINE': 'Medicine',
                    'EQUIPMENT': 'Equipment',
                    'ACCESSORIES': 'Accessories',
                    'EGGS': 'Eggs',
                    'MEAT': 'Meat',
                    'OTHER': 'Other'
                };
                
                categories.forEach(category => {
                    let displayName = categoryNames[category] || category;
                    options += `<option value="${category}">${displayName}</option>`;
                });
                $('#categoryFilter').html(options);
                $('#typeFilter').html(options);
            },
            error: function() {
                console.log('Error loading categories');
            }
        });
    }
    
    // Pagination
    function displayPagination(data) {
        let totalPages = data.total_pages || Math.ceil((data.count || 0) / 20);
        let current = data.current_page || data.page || 1;
        
        if (totalPages <= 1) {
            $('#pagination').empty();
            return;
        }
        
        let html = '<nav class="flex gap-2 flex-wrap justify-center">';
        if (current > 1) {
            html += `<button onclick="goToPage(${current - 1})" class="px-4 py-2 border rounded-lg hover:bg-gray-50">Previous</button>`;
        }
        
        let startPage = Math.max(1, current - 2);
        let endPage = Math.min(totalPages, current + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === current) {
                html += `<button class="px-4 py-2 bg-green-600 text-white rounded-lg">${i}</button>`;
            } else {
                html += `<button onclick="goToPage(${i})" class="px-4 py-2 border rounded-lg hover:bg-gray-50">${i}</button>`;
            }
        }
        
        if (current < totalPages) {
            html += `<button onclick="goToPage(${current + 1})" class="px-4 py-2 border rounded-lg hover:bg-gray-50">Next</button>`;
        }
        html += '</nav>';
        $('#pagination').html(html);
    }
    
    window.goToPage = function(page) {
        currentPage = page;
        loadProducts();
        $('html, body').animate({ scrollTop: 0 }, 'slow');
    };
    
    // Cart functionality
    window.addToCart = function(productId) {
        $.ajax({
            url: '/api/v1/cart/add_item/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                product_id: productId,
                quantity: 1
            }),
            success: function(response) {
                updateCartUI(response);
                showToast('Product added to cart!', 'success');
                loadCart();
            },
            error: function(xhr) {
                let error = xhr.responseJSON?.error || 'Failed to add to cart';
                showToast(error, 'error');
            }
        });
    };
    
    function loadCart() {
        $.ajax({
            url: '/api/v1/cart/view/',
            method: 'GET',
            success: function(response) {
                updateCartUI(response);
            },
            error: function() {
                console.log('Error loading cart');
            }
        });
    }
    
    function updateCartUI(cart) {
        $('#cartCount').text(cart.total_items || 0);
        
        if (cart.items && cart.items.length > 0) {
            let itemsHtml = '';
            cart.items.forEach(item => {
                let imageUrl = item.product_image || '/static/images/placeholder.png';
                itemsHtml += `
                    <div class="flex gap-4 py-3 border-b">
                        <img src="${imageUrl}" class="w-20 h-20 object-cover rounded" onerror="this.src='/static/images/placeholder.png'">
                        <div class="flex-1">
                            <h4 class="font-semibold">${escapeHtml(item.product_name)}</h4>
                            <p class="text-green-600">UGX ${formatNumber(item.price_at_add)}</p>
                            <div class="flex items-center gap-2 mt-2">
                                <button onclick="updateCartItemQuantity(${item.id}, ${item.quantity - 1})" class="px-2 py-1 bg-gray-200 rounded">-</button>
                                <span class="quantity-display" data-item-id="${item.id}">${item.quantity}</span>
                                <button onclick="updateCartItemQuantity(${item.id}, ${item.quantity + 1})" class="px-2 py-1 bg-gray-200 rounded">+</button>
                                <button onclick="removeCartItem(${item.id})" class="ml-2 text-red-600 hover:text-red-800">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        <div class="text-right">
                            <p class="font-semibold">UGX ${formatNumber(item.quantity * item.price_at_add)}</p>
                        </div>
                    </div>
                `;
            });
            $('#cartItems').html(itemsHtml);
            
            let summaryHtml = `
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span>Subtotal:</span>
                        <span>UGX ${formatNumber(cart.subtotal)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Tax (10%):</span>
                        <span>UGX ${formatNumber(cart.tax)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Shipping:</span>
                        <span>UGX ${formatNumber(cart.shipping_cost)}</span>
                    </div>
                    <div class="flex justify-between font-bold text-lg pt-2 border-t">
                        <span>Total:</span>
                        <span>UGX ${formatNumber(cart.total)}</span>
                    </div>
                </div>
            `;
            $('#cartSummary').html(summaryHtml);
        } else {
            $('#cartItems').html('<div class="text-center py-8 text-gray-500">Your cart is empty</div>');
            $('#cartSummary').empty();
        }
    }
    
    window.updateCartItemQuantity = function(itemId, newQuantity) {
        if (newQuantity < 1) {
            removeCartItem(itemId);
            return;
        }
        
        $.ajax({
            url: '/api/v1/cart/update_item/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                item_id: itemId,
                quantity: newQuantity
            }),
            success: function(response) {
                updateCartUI(response);
                loadCart();
            },
            error: function(xhr) {
                showToast(xhr.responseJSON?.error || 'Failed to update quantity', 'error');
            }
        });
    };
    
    window.removeCartItem = function(itemId) {
        $.ajax({
            url: '/api/v1/cart/remove_item/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                item_id: itemId
            }),
            success: function(response) {
                updateCartUI(response);
                loadCart();
                showToast('Item removed from cart', 'success');
            },
            error: function() {
                showToast('Failed to remove item', 'error');
            }
        });
    };
    
    // Apply promo code
    $('#applyPromo').click(function() {
        let promoCode = $('#promoCode').val();
        if (!promoCode) {
            showToast('Please enter a promo code', 'error');
            return;
        }
        
        $.ajax({
            url: '/api/v1/cart/apply_promo/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify({
                promo_code: promoCode
            }),
            success: function(response) {
                showToast(response.message, 'success');
                $('#promoMessage').removeClass('hidden').addClass('text-green-600').text('Promo code applied!');
                loadCart();
            },
            error: function(xhr) {
                let error = xhr.responseJSON?.error || 'Invalid promo code';
                $('#promoMessage').removeClass('hidden').addClass('text-red-600').text(error);
                setTimeout(() => $('#promoMessage').addClass('hidden'), 3000);
            }
        });
    });
    
    // Cart sidebar
    $('#cartButton').click(function() {
        $('#cartSidebar').removeClass('hidden');
        loadCart();
    });
    
    $('#closeCart').click(function() {
        $('#cartSidebar').addClass('hidden');
    });
    
    // Checkout
    $('#checkoutBtn').click(function() {
        loadCartForCheckout();
        $('#checkoutModal').removeClass('hidden');
        $('#cartSidebar').addClass('hidden');
    });
    
    function loadCartForCheckout() {
        $.ajax({
            url: '/api/v1/cart/view/',
            method: 'GET',
            success: function(cart) {
                let summaryHtml = `
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span>Items (${cart.total_items}):</span>
                            <span>UGX ${formatNumber(cart.subtotal)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Tax:</span>
                            <span>UGX ${formatNumber(cart.tax)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Shipping:</span>
                            <span>UGX ${formatNumber(cart.shipping_cost)}</span>
                        </div>
                        <div class="flex justify-between font-bold text-lg pt-2 border-t">
                            <span>Total:</span>
                            <span>UGX ${formatNumber(cart.total)}</span>
                        </div>
                    </div>
                `;
                $('#orderSummary').html(summaryHtml);
            }
        });
    }
    
    $('#checkoutForm').submit(function(e) {
        e.preventDefault();
        
        let orderData = {
            shipping_address: $('#shippingAddress').val(),
            shipping_city: $('#shippingCity').val(),
            shipping_phone: $('#shippingPhone').val(),
            payment_method: $('#paymentMethod').val(),
            notes: $('#orderNotes').val()
        };
        
        // Validate required fields
        if (!orderData.shipping_address || !orderData.shipping_city || !orderData.shipping_phone) {
            showToast('Please fill all shipping details', 'error');
            return;
        }
        
        $.ajax({
            url: '/api/v1/cart/checkout/',
            method: 'POST',
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            data: JSON.stringify(orderData),
            success: function(response) {
                showToast(response.message, 'success');
                $('#checkoutModal').addClass('hidden');
                loadCart();
                setTimeout(() => {
                    window.location.href = `/orders/${response.order_id}/`;
                }, 2000);
            },
            error: function(xhr) {
                let error = xhr.responseJSON?.error || 'Checkout failed';
                showToast(error, 'error');
            }
        });
    });
    
    $('#closeCheckout, #cancelCheckout').click(function() {
        $('#checkoutModal').addClass('hidden');
    });
    
    // Helper functions
    function formatNumber(num) {
        if (!num) return '0';
        return Math.round(num).toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,');
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function showToast(message, type = 'success') {
        let bgColor = type === 'success' ? 'bg-green-600' : 'bg-red-600';
        let toast = $('#toast');
        if (toast.length) {
            toast.removeClass('bg-gray-800 bg-green-600 bg-red-600').addClass(bgColor);
            $('#toastMessage').text(message);
            toast.removeClass('hidden');
            setTimeout(() => {
                toast.addClass('hidden');
            }, 3000);
        } else {
            alert(message);
        }
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            let cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                let cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});