import sys
import os
import importlib.util

# Get the backend directory path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Load the main module directly
spec = importlib.util.spec_from_file_location("main", os.path.join(backend_path, "main.py"))
main_module = importlib.util.module_from_spec(spec)
sys.modules["main"] = main_module
spec.loader.exec_module(main_module)

# Import the function we need to test
parse_api_response = main_module.parse_api_response

class TestAPIResponseParsing:
    """Test API response parsing for each merchant"""
    
    def test_appedia_valid_response(self):
        """Test Appedia response parsing with valid data"""
        response_data = {
            "price": "$4.77",
            "stock": 7
        }
        
        price, in_stock = parse_api_response("Appedia", response_data)
        
        assert price == 4.77
        assert in_stock == True
    
    def test_appedia_out_of_stock(self):
        """Test Appedia response parsing when out of stock"""
        response_data = {
            "price": "$4.77",
            "stock": 0
        }
        
        price, in_stock = parse_api_response("Appedia", response_data)
        
        assert price == 4.77
        assert in_stock == False
    
    def test_appedia_invalid_price_format(self):
        """Test Appedia response parsing with invalid price format"""
        response_data = {
            "price": "invalid",
            "stock": 7
        }
        
        price, in_stock = parse_api_response("Appedia", response_data)
        
        assert price is None
        assert in_stock == False
    
    def test_micromazon_valid_response(self):
        """Test Micromazon response parsing with valid data"""
        response_data = {
            "available": True,
            "price": 5.67
        }
        
        price, in_stock = parse_api_response("Micromazon", response_data)
        
        assert price == 5.67
        assert in_stock == True
    
    def test_micromazon_unavailable(self):
        """Test Micromazon response parsing when unavailable"""
        response_data = {
            "available": False,
            "price": 5.67
        }
        
        price, in_stock = parse_api_response("Micromazon", response_data)
        
        assert price == 5.67
        assert in_stock == False
    
    def test_micromazon_invalid_price(self):
        """Test Micromazon response parsing with invalid price"""
        response_data = {
            "available": True,
            "price": "invalid"
        }
        
        price, in_stock = parse_api_response("Micromazon", response_data)
        
        assert price is None
        assert in_stock == False
    
    def test_googdit_valid_response(self):
        """Test Googdit response parsing with valid data"""
        response_data = {
            "a": [
                {"l": 8839, "q": 4},
                {"l": 1292, "q": 0}
            ],
            "p": 478000000
        }
        
        price, in_stock = parse_api_response("Googdit", response_data)
        
        assert price == 4.78  # 478000000 / 100000000
        assert in_stock == True  # At least one location has stock
    
    def test_googdit_out_of_stock(self):
        """Test Googdit response parsing when out of stock everywhere"""
        response_data = {
            "a": [
                {"l": 8839, "q": 0},
                {"l": 1292, "q": 0}
            ],
            "p": 478000000
        }
        
        price, in_stock = parse_api_response("Googdit", response_data)
        
        assert price == 4.78
        assert in_stock == False
    
    def test_googdit_empty_availability(self):
        """Test Googdit response parsing with empty availability array"""
        response_data = {
            "a": [],
            "p": 478000000
        }
        
        price, in_stock = parse_api_response("Googdit", response_data)
        
        assert price == 4.78
        assert in_stock == False
    
    def test_googdit_invalid_price(self):
        """Test Googdit response parsing with invalid price"""
        response_data = {
            "a": [
                {"l": 8839, "q": 4}
            ],
            "p": None
        }
        
        price, in_stock = parse_api_response("Googdit", response_data)
        
        assert price is None
        assert in_stock == False
    
    def test_unknown_merchant(self):
        """Test response parsing for unknown merchant"""
        response_data = {
            "price": "$4.77",
            "stock": 7
        }
        
        price, in_stock = parse_api_response("Unknown", response_data)
        
        assert price is None
        assert in_stock == False
    
    def test_case_insensitive_merchant_names(self):
        """Test that merchant names are case insensitive"""
        response_data = {
            "price": "$4.77",
            "stock": 7
        }
        
        price, in_stock = parse_api_response("APPEDIA", response_data)
        
        assert price == 4.77
        assert in_stock == True