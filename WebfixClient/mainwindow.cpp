#include "mainwindow.h"
#include "apiclient.h"
#include "authsession.h"
#include "streamclient.h"
#include "loginwidget.h"
#include "registerwidget.h"
#include "forgotpasswordwidget.h"
#include "chatwidget.h"
#include "usermenudialog.h"
#include "adminmenudialog.h"

#include <QStackedWidget>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_api(new ApiClient(this))
    , m_auth(new AuthSession(m_api, this))
    , m_stream(new StreamClient(m_api, this))
{
    setWindowTitle(QStringLiteral("Webfix Chat"));
    resize(960, 640);

    m_stack = new QStackedWidget(this);
    setCentralWidget(m_stack);

    m_loginPage = new LoginWidget(m_api, m_auth, this);
    m_registerPage = new RegisterWidget(m_api, this);
    m_forgotPasswordPage = new ForgotPasswordWidget(m_api, this);
    m_chatPage = new ChatWidget(m_api, m_auth, m_stream, this);

    m_stack->addWidget(m_loginPage);
    m_stack->addWidget(m_registerPage);
    m_stack->addWidget(m_forgotPasswordPage);
    m_stack->addWidget(m_chatPage);

    connect(m_loginPage, &LoginWidget::registerRequested, this, [this]() {
        m_registerPage->reset();
        m_stack->setCurrentWidget(m_registerPage);
    });
    connect(m_loginPage, &LoginWidget::forgotPasswordRequested, this, [this]() {
        m_forgotPasswordPage->reset();
        m_stack->setCurrentWidget(m_forgotPasswordPage);
    });
    connect(m_registerPage, &RegisterWidget::backToLoginRequested, this, &MainWindow::showLogin);
    connect(m_forgotPasswordPage, &ForgotPasswordWidget::backToLoginRequested, this, &MainWindow::showLogin);

    connect(m_auth, &AuthSession::loggedInChanged, this, &MainWindow::showChat);
    connect(m_auth, &AuthSession::loggedOut, this, &MainWindow::showLogin);

    connect(m_chatPage, &ChatWidget::openUserMenuRequested, this, &MainWindow::openUserMenu);
    connect(m_chatPage, &ChatWidget::openAdminMenuRequested, this, &MainWindow::openAdminMenu);

    showLogin();
    m_auth->tryAutoLogin();
}

void MainWindow::showLogin()
{
    m_chatPage->stop();
    m_loginPage->refreshPublicInfo();
    m_stack->setCurrentWidget(m_loginPage);
}

void MainWindow::showChat()
{
    m_chatPage->start();
    m_stack->setCurrentWidget(m_chatPage);
}

void MainWindow::openUserMenu()
{
    UserMenuDialog dialog(m_api, m_auth, this);
    dialog.reload();
    dialog.exec();
}

void MainWindow::openAdminMenu()
{
    AdminMenuDialog dialog(m_api, m_auth, this);
    dialog.reload();
    dialog.exec();
}
