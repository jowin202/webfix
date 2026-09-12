#include "adminmenudialog.h"
#include "apiclient.h"
#include "authsession.h"

#include <QVBoxLayout>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QCheckBox>
#include <QSpinBox>
#include <QLineEdit>
#include <QTableWidget>
#include <QHeaderView>
#include <QComboBox>
#include <QLabel>
#include <QPushButton>
#include <QGroupBox>
#include <QJsonArray>
#include <QJsonObject>

namespace {
const QStringList kSettingKeys = {
    "allow_guest_login", "activate_timeout", "mandatory_user_verification",
    "user_verification_mail", "user_verification_fediverse",
    "timeout_time", "pw_recovery_token_valid_time", "pw_min_len",
    "announcement_general", "announcement_guests", "announcement_registered_users", "announcement_team",
};
}

AdminMenuDialog::AdminMenuDialog(ApiClient *api, AuthSession *auth, QWidget *parent)
    : QDialog(parent)
    , m_api(api)
    , m_auth(auth)
{
    setWindowTitle(QStringLiteral("Admin"));
    resize(640, 520);

    auto *root = new QVBoxLayout(this);

    auto *settingsBox = new QGroupBox(QStringLiteral("Settings"));
    auto *form = new QFormLayout(settingsBox);
    m_allowGuestLogin = new QCheckBox();
    m_activateTimeout = new QCheckBox();
    m_mandatoryUserVerification = new QCheckBox();
    m_userVerificationMail = new QCheckBox();
    m_userVerificationFediverse = new QCheckBox();
    m_timeoutTime = new QSpinBox();
    m_timeoutTime->setRange(0, 86400);
    m_pwRecoveryTokenValidTime = new QSpinBox();
    m_pwRecoveryTokenValidTime->setRange(0, 86400);
    m_pwMinLen = new QSpinBox();
    m_pwMinLen->setRange(0, 64);
    m_announcementGeneral = new QLineEdit();
    m_announcementGuests = new QLineEdit();
    m_announcementRegisteredUsers = new QLineEdit();
    m_announcementTeam = new QLineEdit();

    form->addRow(QStringLiteral("Allow guest login:"), m_allowGuestLogin);
    form->addRow(QStringLiteral("Enable idle timeout:"), m_activateTimeout);
    form->addRow(QStringLiteral("Mandatory user verification:"), m_mandatoryUserVerification);
    form->addRow(QStringLiteral("Verify via e-mail:"), m_userVerificationMail);
    form->addRow(QStringLiteral("Verify via fediverse:"), m_userVerificationFediverse);
    form->addRow(QStringLiteral("Timeout (seconds):"), m_timeoutTime);
    form->addRow(QStringLiteral("Password recovery token valid (seconds):"), m_pwRecoveryTokenValidTime);
    form->addRow(QStringLiteral("Minimum password length:"), m_pwMinLen);
    form->addRow(QStringLiteral("Announcement (general):"), m_announcementGeneral);
    form->addRow(QStringLiteral("Announcement (guests):"), m_announcementGuests);
    form->addRow(QStringLiteral("Announcement (registered users):"), m_announcementRegisteredUsers);
    form->addRow(QStringLiteral("Announcement (team):"), m_announcementTeam);

    m_settingsMessage = new QLabel();
    m_settingsMessage->hide();
    form->addRow(m_settingsMessage);

    auto *saveSettingsButton = new QPushButton(QStringLiteral("Save settings"));
    form->addRow(saveSettingsButton);
    root->addWidget(settingsBox);

    auto *usersBox = new QGroupBox(QStringLiteral("Users"));
    auto *usersLayout = new QVBoxLayout(usersBox);
    m_userTable = new QTableWidget(0, 5);
    m_userTable->setHorizontalHeaderLabels({"ID", "Username", "Admin", "Kicked until", "Muted until"});
    m_userTable->horizontalHeader()->setStretchLastSection(true);
    m_userTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_userTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    usersLayout->addWidget(m_userTable, 1);

    auto *actionRow = new QHBoxLayout();
    m_durationCombo = new QComboBox();
    m_durationCombo->addItem(QStringLiteral("1 minute"), 60);
    m_durationCombo->addItem(QStringLiteral("5 minutes"), 300);
    m_durationCombo->addItem(QStringLiteral("1 hour"), 3600);
    m_durationCombo->addItem(QStringLiteral("1 day"), 86400);
    m_durationCombo->addItem(QStringLiteral("Permanent"), -1);
    m_silentCheckbox = new QCheckBox(QStringLiteral("Silent"));
    auto *kickButton = new QPushButton(QStringLiteral("Kick"));
    auto *unkickButton = new QPushButton(QStringLiteral("Unkick"));
    auto *muteButton = new QPushButton(QStringLiteral("Mute"));
    auto *unmuteButton = new QPushButton(QStringLiteral("Unmute"));
    actionRow->addWidget(m_durationCombo);
    actionRow->addWidget(m_silentCheckbox);
    actionRow->addWidget(kickButton);
    actionRow->addWidget(unkickButton);
    actionRow->addWidget(muteButton);
    actionRow->addWidget(unmuteButton);
    usersLayout->addLayout(actionRow);

    m_userMessage = new QLabel();
    m_userMessage->hide();
    usersLayout->addWidget(m_userMessage);

    root->addWidget(usersBox, 1);

    auto *closeButton = new QPushButton(QStringLiteral("Close"));
    root->addWidget(closeButton);

    connect(saveSettingsButton, &QPushButton::clicked, this, &AdminMenuDialog::saveSettings);
    connect(kickButton, &QPushButton::clicked, this, &AdminMenuDialog::kickSelected);
    connect(unkickButton, &QPushButton::clicked, this, &AdminMenuDialog::unkickSelected);
    connect(muteButton, &QPushButton::clicked, this, &AdminMenuDialog::muteSelected);
    connect(unmuteButton, &QPushButton::clicked, this, &AdminMenuDialog::unmuteSelected);
    connect(closeButton, &QPushButton::clicked, this, &QDialog::accept);
}

void AdminMenuDialog::reload()
{
    loadSettings();
    loadUsers();
}

void AdminMenuDialog::loadSettings()
{
    m_settingsMessage->hide();
    QJsonArray keys;
    for (const QString &k : kSettingKeys) {
        keys.append(k);
    }
    m_api->postJsonDoc("/api/admin/settings/get_settings/", m_auth->token, QJsonDocument(keys),
                        [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result)) {
            return;
        }
        const QJsonObject obj = result.toObject();
        m_allowGuestLogin->setChecked(obj.value("allow_guest_login").toBool());
        m_activateTimeout->setChecked(obj.value("activate_timeout").toBool());
        m_mandatoryUserVerification->setChecked(obj.value("mandatory_user_verification").toBool());
        m_userVerificationMail->setChecked(obj.value("user_verification_mail").toBool());
        m_userVerificationFediverse->setChecked(obj.value("user_verification_fediverse").toBool());
        m_timeoutTime->setValue(obj.value("timeout_time").toInt());
        m_pwRecoveryTokenValidTime->setValue(obj.value("pw_recovery_token_valid_time").toInt());
        m_pwMinLen->setValue(obj.value("pw_min_len").toInt());
        m_announcementGeneral->setText(obj.value("announcement_general").toString());
        m_announcementGuests->setText(obj.value("announcement_guests").toString());
        m_announcementRegisteredUsers->setText(obj.value("announcement_registered_users").toString());
        m_announcementTeam->setText(obj.value("announcement_team").toString());
    });
}

void AdminMenuDialog::saveSettings()
{
    m_settingsMessage->hide();
    const QJsonObject body{
        {"allow_guest_login", m_allowGuestLogin->isChecked()},
        {"activate_timeout", m_activateTimeout->isChecked()},
        {"mandatory_user_verification", m_mandatoryUserVerification->isChecked()},
        {"user_verification_mail", m_userVerificationMail->isChecked()},
        {"user_verification_fediverse", m_userVerificationFediverse->isChecked()},
        {"timeout_time", m_timeoutTime->value()},
        {"pw_recovery_token_valid_time", m_pwRecoveryTokenValidTime->value()},
        {"pw_min_len", m_pwMinLen->value()},
        {"announcement_general", m_announcementGeneral->text()},
        {"announcement_guests", m_announcementGuests->text()},
        {"announcement_registered_users", m_announcementRegisteredUsers->text()},
        {"announcement_team", m_announcementTeam->text()},
    };
    m_api->postJson("/api/admin/settings/set_settings/", m_auth->token, body, [this](const QJsonValue &result, int) {
        const bool ok = !ApiClient::isError(result) && result.toObject().value("status").toString() == "success";
        m_settingsMessage->setStyleSheet(ok ? "color: green;" : "color: red;");
        m_settingsMessage->setText(ok ? QStringLiteral("Settings saved.") : QStringLiteral("Failed to save settings."));
        m_settingsMessage->show();
    });
}

void AdminMenuDialog::loadUsers()
{
    m_api->get("/api/admin/userdb/get_all_users/", m_auth->token, [this](const QJsonValue &result, int) {
        if (ApiClient::isError(result) || !result.isArray()) {
            return;
        }
        const QJsonArray arr = result.toArray();
        m_userTable->setRowCount(arr.size());
        for (int row = 0; row < arr.size(); ++row) {
            const QJsonObject obj = arr[row].toObject();
            auto *idItem = new QTableWidgetItem(QString::number(obj.value("id").toInt()));
            idItem->setData(Qt::UserRole, obj.value("id").toInt());
            m_userTable->setItem(row, 0, idItem);
            m_userTable->setItem(row, 1, new QTableWidgetItem(obj.value("username").toString()));
            m_userTable->setItem(row, 2, new QTableWidgetItem(QString::number(obj.value("admin").toInt())));
            m_userTable->setItem(row, 3, new QTableWidgetItem(obj.value("kicked_until").toString()));
            m_userTable->setItem(row, 4, new QTableWidgetItem(obj.value("muted_until").toString()));
        }
    });
}

int AdminMenuDialog::selectedUserId() const
{
    const auto selected = m_userTable->selectionModel() ? m_userTable->selectionModel()->selectedRows() : QModelIndexList();
    if (selected.isEmpty()) {
        return -1;
    }
    QTableWidgetItem *idItem = m_userTable->item(selected.first().row(), 0);
    return idItem ? idItem->data(Qt::UserRole).toInt() : -1;
}

int AdminMenuDialog::selectedDurationSeconds() const
{
    return m_durationCombo->currentData().toInt();
}

void AdminMenuDialog::kickSelected()
{
    const int userId = selectedUserId();
    if (userId < 0) {
        return;
    }
    const QJsonObject body{{"silent", m_silentCheckbox->isChecked()}, {"user_id", userId}, {"time", selectedDurationSeconds()}};
    m_api->postJson("/api/admin/kick_user/", m_auth->token, body, [this](const QJsonValue &, int) {
        m_userMessage->setText(QStringLiteral("Kick applied."));
        m_userMessage->show();
        loadUsers();
    });
}

void AdminMenuDialog::unkickSelected()
{
    const int userId = selectedUserId();
    if (userId < 0) {
        return;
    }
    const QJsonObject body{{"silent", true}, {"user_id", userId}, {"time", 0}};
    m_api->postJson("/api/admin/kick_user/", m_auth->token, body, [this](const QJsonValue &, int) {
        m_userMessage->setText(QStringLiteral("Unkicked."));
        m_userMessage->show();
        loadUsers();
    });
}

void AdminMenuDialog::muteSelected()
{
    const int userId = selectedUserId();
    if (userId < 0) {
        return;
    }
    const QJsonObject body{{"silent", m_silentCheckbox->isChecked()}, {"user_id", userId}, {"time", selectedDurationSeconds()}};
    m_api->postJson("/api/admin/mute_user/", m_auth->token, body, [this](const QJsonValue &, int) {
        m_userMessage->setText(QStringLiteral("Mute applied."));
        m_userMessage->show();
        loadUsers();
    });
}

void AdminMenuDialog::unmuteSelected()
{
    const int userId = selectedUserId();
    if (userId < 0) {
        return;
    }
    const QJsonObject body{{"silent", true}, {"user_id", userId}, {"time", 0}};
    m_api->postJson("/api/admin/mute_user/", m_auth->token, body, [this](const QJsonValue &, int) {
        m_userMessage->setText(QStringLiteral("Unmuted."));
        m_userMessage->show();
        loadUsers();
    });
}
