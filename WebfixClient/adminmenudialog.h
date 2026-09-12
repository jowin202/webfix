#ifndef ADMINMENUDIALOG_H
#define ADMINMENUDIALOG_H

#include <QDialog>
#include <QMap>

class ApiClient;
class AuthSession;
class QCheckBox;
class QSpinBox;
class QLineEdit;
class QTableWidget;
class QComboBox;
class QLabel;

// Mirrors frontend/src/app/components/admin-menu/admin-menu.component:
// global settings form and the user kick/mute table. Only what that
// component actually exposes today (settings + kick/mute) -- the backend
// also has reset_database/delete_id/global-announcement endpoints that the
// web client itself never surfaces, so they're left out here too for
// faithful parity.
class AdminMenuDialog : public QDialog
{
    Q_OBJECT
public:
    AdminMenuDialog(ApiClient *api, AuthSession *auth, QWidget *parent = nullptr);

    void reload();

private:
    ApiClient *m_api;
    AuthSession *m_auth;

    QCheckBox *m_allowGuestLogin;
    QCheckBox *m_activateTimeout;
    QCheckBox *m_mandatoryUserVerification;
    QCheckBox *m_userVerificationMail;
    QCheckBox *m_userVerificationFediverse;
    QSpinBox *m_timeoutTime;
    QSpinBox *m_pwRecoveryTokenValidTime;
    QSpinBox *m_pwMinLen;
    QLineEdit *m_announcementGeneral;
    QLineEdit *m_announcementGuests;
    QLineEdit *m_announcementRegisteredUsers;
    QLineEdit *m_announcementTeam;
    QLabel *m_settingsMessage;

    QTableWidget *m_userTable;
    QComboBox *m_durationCombo;
    QCheckBox *m_silentCheckbox;
    QLabel *m_userMessage;

    void loadSettings();
    void saveSettings();
    void loadUsers();
    int selectedUserId() const;
    int selectedDurationSeconds() const;
    void kickSelected();
    void muteSelected();
    void unkickSelected();
    void unmuteSelected();
};

#endif // ADMINMENUDIALOG_H
