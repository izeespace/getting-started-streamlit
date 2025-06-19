import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import User, Customer, Product, LeadAssignment, Sale, PackingRequest

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_default_users():
    db = SessionLocal()
    if not db.query(User).count():
        db.add_all([
            User(username='admin', password='admin', role='Admin'),
            User(username='manager', password='manager', role='Manager'),
            User(username='agent', password='agent', role='Sales'),
            User(username='packer', password='packer', role='Packing'),
        ])
        db.commit()
    db.close()

create_default_users()

if 'user' not in st.session_state:
    st.session_state.user = None


def login():
    st.title('Login')
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        db = SessionLocal()
        user = db.query(User).filter_by(username=username, password=password).first()
        db.close()
        if user:
            st.session_state.user = {'id': user.id, 'username': user.username, 'role': user.role}
            st.experimental_rerun()
        else:
            st.error('Invalid credentials')


def sidebar_menu():
    role = st.session_state.user['role']
    menu = []
    if role in ['Admin', 'Manager']:
        menu.extend(['Customers', 'Products', 'Assignments', 'Reports'])
    if role == 'Sales':
        menu.append('My Leads')
    if role == 'Packing':
        menu.append('Packing')
    if role == 'Admin':
        menu.append('Users')
    return st.sidebar.radio('Menu', menu)


def customers_page(db: Session):
    st.header('Customers')
    action = st.selectbox('Action', ['View', 'Add'])
    if action == 'Add':
        with st.form('add_customer'):
            name = st.text_input('Name')
            phone = st.text_input('Phone')
            email = st.text_input('Email')
            address = st.text_input('Address')
            note = st.text_area('Note')
            status = st.selectbox('Status', ['New', 'Contacted', 'Closed'])
            submitted = st.form_submit_button('Save')
            if submitted:
                db.add(Customer(name=name, phone=phone, email=email,
                                address=address, note=note, status=status))
                db.commit()
                st.success('Customer added')
    customers = db.query(Customer).all()
    st.subheader('All Customers')
    st.table([{c.id, c.name, c.status} for c in customers])


def products_page(db: Session):
    st.header('Products')
    action = st.selectbox('Action', ['View', 'Add'])
    if action == 'Add':
        with st.form('add_product'):
            name = st.text_input('Name')
            price = st.number_input('Price', min_value=0.0)
            description = st.text_area('Description')
            quantity = st.number_input('Inventory Quantity', min_value=0, step=1)
            status = st.selectbox('Status', ['Active', 'Inactive'])
            submitted = st.form_submit_button('Save')
            if submitted:
                db.add(Product(name=name, price=price, description=description,
                               quantity=quantity, status=status))
                db.commit()
                st.success('Product added')
    products = db.query(Product).all()
    st.subheader('All Products')
    st.table([{p.id, p.name, p.quantity} for p in products])


def assignments_page(db: Session):
    st.header('Lead Assignment')
    customers = db.query(Customer).filter(Customer.assigned_agent_id == None).all()
    agents = db.query(User).filter_by(role='Sales').all()
    customer = st.selectbox('Customer', customers, format_func=lambda x: f"{x.id} {x.name}")
    agent = st.selectbox('Agent', agents, format_func=lambda x: x.username)
    if st.button('Assign'):
        customer.assigned_agent_id = agent.id
        db.add(LeadAssignment(customer_id=customer.id, agent_id=agent.id))
        db.commit()
        st.success('Assigned')
    st.subheader('Assignment History')
    history = db.query(LeadAssignment).all()
    st.table([{h.customer_id, h.agent_id, h.assigned_at} for h in history])


def sales_page(db: Session):
    st.header('My Leads')
    user_id = st.session_state.user['id']
    leads = db.query(Customer).filter_by(assigned_agent_id=user_id).all()
    for lead in leads:
        with st.expander(f"{lead.name} - {lead.status}"):
            sale = db.query(Sale).filter_by(customer_id=lead.id, agent_id=user_id).first()
            if not sale:
                sale = Sale(customer_id=lead.id, agent_id=user_id)
                db.add(sale)
                db.commit()
            status = st.selectbox('Status', ['Interested', 'Not Interested', 'Closed'], index=['Interested','Not Interested','Closed'].index(sale.status), key=f'status{lead.id}')
            note = st.text_area('Note', value=sale.note or '', key=f'note{lead.id}')
            follow = st.date_input('Follow up', value=sale.follow_up if sale.follow_up else datetime.today(), key=f'fup{lead.id}')
            if st.button('Save', key=f'save{lead.id}'):
                sale.status = status
                sale.note = note
                sale.follow_up = follow
                if status == 'Closed' and not sale.closed_at:
                    product = st.selectbox('Product', db.query(Product).all(), format_func=lambda x: x.name, key=f'prod{lead.id}')
                    if product.quantity < 1:
                        st.error('Out of stock')
                    else:
                        sale.product_id = product.id
                        sale.closed_at = datetime.utcnow()
                        product.quantity -= 1
                        db.add(PackingRequest(sale_id=sale.id))
                        db.commit()
                        st.success('Sale closed and packing requested')
                else:
                    db.commit()
                    st.success('Updated')


def reports_page(db: Session):
    st.header('Reports')
    agents = db.query(User).filter_by(role='Sales').all()
    for agent in agents:
        total = db.query(Customer).filter_by(assigned_agent_id=agent.id).count()
        closed = db.query(Sale).filter_by(agent_id=agent.id, status='Closed').count()
        st.write(f"Agent {agent.username}: leads={total}, closed={closed}")


def packing_page(db: Session):
    st.header('Packing Requests')
    requests = db.query(PackingRequest).filter_by(status='Pending').all()
    for req in requests:
        sale = req.sale
        customer = db.query(Customer).get(sale.customer_id)
        product = db.query(Product).get(sale.product_id)
        with st.expander(f"Order {req.id} - {customer.name}"):
            st.write(f"Product: {product.name}")
            shipping = st.text_input('Shipping info', key=f'ship{req.id}')
            status = st.selectbox('Status', ['Pending', 'Packed', 'Shipped'], key=f'status{req.id}')
            if st.button('Update', key=f'up{req.id}'):
                req.shipping_info = shipping
                req.status = status
                req.updated_at = datetime.utcnow()
                db.commit()
                st.success('Updated')


def users_page(db: Session):
    st.header('Users')
    action = st.selectbox('Action', ['View', 'Add'])
    if action == 'Add':
        with st.form('add_user'):
            username = st.text_input('Username')
            password = st.text_input('Password')
            role = st.selectbox('Role', ['Admin', 'Manager', 'Sales', 'Packing'])
            submitted = st.form_submit_button('Save')
            if submitted:
                db.add(User(username=username, password=password, role=role))
                db.commit()
                st.success('User added')
    users = db.query(User).all()
    st.table([{u.id, u.username, u.role} for u in users])


def main():
    if not st.session_state.user:
        login()
        return
    db = SessionLocal()
    page = sidebar_menu()
    if page == 'Customers':
        customers_page(db)
    elif page == 'Products':
        products_page(db)
    elif page == 'Assignments':
        assignments_page(db)
    elif page == 'Reports':
        reports_page(db)
    elif page == 'My Leads':
        sales_page(db)
    elif page == 'Packing':
        packing_page(db)
    elif page == 'Users':
        users_page(db)
    db.close()

if __name__ == '__main__':
    main()
