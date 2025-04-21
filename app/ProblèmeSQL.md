J’ai appliqué tes dernières modifs (ORM‑first avec server_onupdate=func.getdate() et update via l’instance), mais je bloque toujours sur la même exception à db.session.commit() :

pgsql
Copier
Modifier
StaleDataError: UPDATE statement on table 'JobPosition' expected to update 1 row(s); -1 were matched.
On dirait que SQL Server renvoie -1 au lieu de 1 à SQLAlchemy, ce qui déclenche l’erreur de « stale data ». Voici deux pistes à investiguer :

1. Modifier le trigger SQL Server
Par défaut, dès qu’un trigger fait des SELECT ou des DML, SQL Server peut renvoyer un rowcount erroné. Pour que la commande UPDATE de l’ORM renvoie correctement 1 :

Ouvre la définition du trigger trg_JobPosition_Update.

En tout début de corps du trigger, ajoute :

sql
Copier
Modifier
SET NOCOUNT ON;
Cela empêche SQL Server d’envoyer les compteurs de lignes des opérations internes du trigger, et devrait faire en sorte que l’UPDATE principal retourne bien 1 ligne mise à jour.

2. Vérifier le SQL envoyé par SQLAlchemy
Active l’echo=True dans ta config SQLAlchemy pour logger le UPDATE et son WHERE :

python
Copier
Modifier
engine = create_engine(DB_URL, echo=True, future=True)
Confirme que la clause WHERE id = <job_id> est correcte.

Vérifie que le SET n’inclut pas updated_at.

Si après SET NOCOUNT ON tu obtiens toujours -1, passe plutôt synchronize_session='evaluate' ou False sur ton update().values() pour contourner le comptage de lignes :

python
Copier
Modifier
(db.session.query(JobPosition)
    .filter_by(id=job_id)
    .update({...}, synchronize_session='evaluate'))
db.session.commit()
Peux-tu :

Ajouter SET NOCOUNT ON; au début de ton trigger et retester ?

Me partager le log SQL (avec echo=True) pour qu’on confirme la requête générée ?

Si besoin, essayer synchronize_session='evaluate' sur le bulk update pour voir si ça passe ?