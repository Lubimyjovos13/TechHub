# Auth Testing (TeachHub)

Token-based JWT (Bearer). Frontend stores token in localStorage `th_token`.

## Accounts
- Admin: admin@teachhub.com / admin12345
- Teacher: teacher@teachhub.com / teacher12345

## API test
```
API=https://assignment-vault-2.preview.emergentagent.com/api
# register
curl -s -X POST $API/auth/register -H "Content-Type: application/json" -d '{"email":"new@t.com","password":"pass12345","name":"New Teacher"}'
# login
TOKEN=$(curl -s -X POST $API/auth/login -H "Content-Type: application/json" -d '{"email":"teacher@teachhub.com","password":"teacher12345"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s $API/auth/me -H "Authorization: Bearer $TOKEN"
```
