Notification de modification de la structure de base de données ATS_CV
Chers développeurs,
Nous avons récemment effectué une refactorisation majeure de la structure de notre base de données ATS_CV pour améliorer la normalisation et la gestion des départements. Voici un résumé complet des modifications apportées :
1. Création d'une table Department dédiée
Nous avons créé une nouvelle table Department avec la structure suivante :
sqlCREATE TABLE [dbo].[Department](
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [name] NVARCHAR(100) NOT NULL UNIQUE,
    [description] NVARCHAR(255) NULL,
    [created_at] DATETIME DEFAULT GETDATE(),
    [updated_at] DATETIME DEFAULT GETDATE()
);
2. Migration des attributs de départements
Les champs department des tables User et JobPosition ont été remplacés par des références vers cette nouvelle table :

Suppression des colonnes department (chaînes de caractères)
Ajout des colonnes department_id (clés étrangères)
Établissement des contraintes d'intégrité référentielle

3. Contraintes de clé étrangère ajoutées
sqlALTER TABLE [dbo].[User] ADD CONSTRAINT FK_User_Department 
FOREIGN KEY ([department_id]) REFERENCES [dbo].[Department]([id]);

ALTER TABLE [dbo].[JobPosition] ADD CONSTRAINT FK_JobPosition_Department 
FOREIGN KEY ([department_id]) REFERENCES [dbo].[Department]([id]);
4. Liste des départements standardisés
Nous avons normalisé les départements avec une liste officielle :

Direction Générale
Ressources Humaines
Finance et Comptabilité
Marketing
Ventes
Informatique
Recherche et Développement
Production
Logistique
Service Client
Juridique
Qualité

5. Mise à jour des vues
La vue vw_ApplicationStats a été mise à jour pour inclure le nom du département :
sqlCREATE VIEW [dbo].[vw_ApplicationStats] AS
SELECT 
    JP.title AS job_title,
    D.name AS department_name,
    COUNT(A.id) AS total_applications,
    -- Autres agrégations...
FROM [dbo].[JobPosition] JP
LEFT JOIN [dbo].[Department] D ON JP.department_id = D.id
LEFT JOIN [dbo].[Application] A ON JP.id = A.job_position_id
GROUP BY JP.id, JP.title, D.name;
6. Index pour les performances
Nous avons ajouté un index pour améliorer les performances des requêtes filtrant par département :
sqlCREATE INDEX IDX_JobPosition_Department ON [dbo].[JobPosition]([department_id]);
Impacts sur le code et actions requises

Mise à jour des requêtes SQL : Toutes les requêtes faisant référence à User.department ou JobPosition.department doivent être modifiées pour utiliser department_id et joindre la table Department au besoin.
Mise à jour des classes d'entités :

Remplacer la propriété String department par Integer departmentId
Ajouter une nouvelle entité Department avec mappings appropriés
Mettre à jour les relations JPA/Hibernate


Mise à jour des formulaires :

Les champs de texte libre pour le département doivent être remplacés par des listes déroulantes
Ces listes doivent être alimentées depuis la table Department


Mise à jour des filtres de recherche :

Adapter les critères de recherche par département


Modification des APIs :

Les endpoints renvoyant/acceptant des informations de département doivent être mis à jour
Documentation à adapter en conséquence



Exemple de code pour obtenir les départements
java// Ancienne méthode (à remplacer)
String userDepartment = user.getDepartment();

// Nouvelle méthode
Department userDepartment = departmentRepository.findById(user.getDepartmentId()).orElse(null);
String departmentName = userDepartment != null ? userDepartment.getName() : "";
Calendrier de déploiement
Ces modifications ont déjà été appliquées à la base de données de développement. Merci de mettre à jour votre code et de tester vos modifications avant la prochaine réunion d'équipe.