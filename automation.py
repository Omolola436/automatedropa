"""
Automation features for GDPR ROPA system
"""

def auto_classify_data(description):
    """Auto-classify data based on description keywords"""
    description_lower = description.lower()
    
    # Keywords for different categories
    category_keywords = {
        "Human Resources": ["employee", "hr", "staff", "personnel", "payroll", "recruitment", "hiring"],
        "Marketing": ["marketing", "campaign", "newsletter", "advertising", "promotion", "lead"],
        "Sales": ["sales", "customer", "order", "purchase", "transaction", "invoice"],
        "Customer Service": ["support", "service", "complaint", "feedback", "help", "assistance"],
        "IT Security": ["security", "access", "login", "authentication", "system", "network"],
        "Finance": ["finance", "accounting", "payment", "billing", "financial", "budget"],
        "Operations": ["operations", "logistics", "supply", "inventory", "procurement"],
        "Legal": ["legal", "contract", "compliance", "regulatory", "audit", "governance"],
        "Training": ["training", "education", "learning", "development", "course", "certification"]
    }
    
    # Score each category based on keyword matches
    category_scores = {}
    for category, keywords in category_keywords.items():
        score = sum(1 for keyword in keywords if keyword in description_lower)
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or default
    if category_scores:
        return max(category_scores, key=category_scores.get)
    else:
        return "Administration"

def suggest_processing_purpose(department, category=""):
    """Suggest processing purpose based on department and category"""
    
    purpose_mapping = {
        "HR": {
            "default": "Human resources management and employee administration",
            "Human Resources": "Employee data processing for HR operations including recruitment, performance management, and payroll"
        },
        "IT": {
            "default": "IT systems management and security administration",
            "IT Security": "System access control, security monitoring, and compliance management"
        },
        "Marketing": {
            "default": "Marketing activities and customer communication",
            "Marketing": "Direct marketing, lead generation, and customer relationship management"
        },
        "Sales": {
            "default": "Sales process management and customer relations",
            "Sales": "Customer order processing, sales pipeline management, and contract administration"
        },
        "Finance": {
            "default": "Financial operations and accounting processes",
            "Finance": "Financial transaction processing, billing, and regulatory compliance"
        },
        "Legal": {
            "default": "Legal compliance and risk management",
            "Legal": "Legal compliance monitoring, contract management, and regulatory reporting"
        }
    }
    
    dept_purposes = purpose_mapping.get(department, {"default": "Business operations and administration"})
    return dept_purposes.get(category, dept_purposes["default"])

def assess_risk(data_categories, special_categories):
    """Assess privacy risk based on data categories"""
    
    risk_factors = {
        "high_risk_data": ["Genetic Data", "Biometric Data", "Health Data", "Criminal Convictions"],
        "medium_risk_data": ["Financial Data", "Location Data", "Behavioral Data"],
        "personal_identifiers": ["Identity Data", "Contact Information"]
    }
    
    risk_score = 0
    risk_reasons = []
    
    # Check for special categories (high risk)
    if special_categories:
        special_list = [cat.strip() for cat in special_categories.split(',') if cat.strip()]
        high_risk_special = [cat for cat in special_list if cat in risk_factors["high_risk_data"]]
        if high_risk_special:
            risk_score += 3
            risk_reasons.append(f"Special categories detected: {', '.join(high_risk_special)}")
    
    # Check for high-risk regular data
    if data_categories:
        data_list = [cat.strip() for cat in data_categories.split(',') if cat.strip()]
        high_risk_data = [cat for cat in data_list if cat in risk_factors["high_risk_data"]]
        medium_risk_data = [cat for cat in data_list if cat in risk_factors["medium_risk_data"]]
        
        if high_risk_data:
            risk_score += 2
            risk_reasons.append(f"High-risk data categories: {', '.join(high_risk_data)}")
        
        if medium_risk_data:
            risk_score += 1
            risk_reasons.append(f"Medium-risk data categories: {', '.join(medium_risk_data)}")
    
    # Determine overall risk level
    if risk_score >= 3:
        risk_level = "High"
        dpia_required = "Yes"
    elif risk_score >= 2:
        risk_level = "Medium"
        dpia_required = "Consider"
    else:
        risk_level = "Low"
        dpia_required = "No"
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "dpia_required": dpia_required,
        "risk_reasons": risk_reasons
    }

def suggest_security_measures(data_categories, risk_level):
    """Suggest appropriate security measures based on data and risk"""
    
    base_measures = [
        "Access controls and user authentication",
        "Regular data backups",
        "Encryption of data in transit and at rest",
        "Staff training on data protection"
    ]
    
    # Risk-based additional measures
    risk_measures = {
        "High": [
            "Multi-factor authentication",
            "Data loss prevention (DLP) tools",
            "Regular penetration testing",
            "Incident response procedures",
            "Data minimization and pseudonymization",
            "Regular security audits"
        ],
        "Medium": [
            "Enhanced access logging and monitoring",
            "Regular security updates and patches",
            "Data retention policy enforcement",
            "Vendor security assessments"
        ],
        "Low": [
            "Basic firewall protection",
            "Antivirus software",
            "Regular password updates"
        ]
    }
    
    # Data-specific measures
    data_specific_measures = {
        "Health Data": ["Medical data encryption", "HIPAA compliance measures"],
        "Financial Data": ["PCI DSS compliance", "Financial data segregation"],
        "Biometric Data": ["Biometric data hashing", "Secure biometric storage"],
        "Location Data": ["Location data anonymization", "GPS data encryption"]
    }
    
    measures = base_measures.copy()
    
    # Add risk-based measures
    measures.extend(risk_measures.get(risk_level, []))
    
    # Add data-specific measures
    if data_categories:
        data_list = [cat.strip() for cat in data_categories.split(',') if cat.strip()]
        for data_type in data_list:
            if data_type in data_specific_measures:
                measures.extend(data_specific_measures[data_type])
    
    return "; ".join(measures)
